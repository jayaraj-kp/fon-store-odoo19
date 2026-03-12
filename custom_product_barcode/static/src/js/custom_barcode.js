/** @odoo-module */
/**
 * custom_barcode.js  –  Odoo 19 CE  (v26)
 *
 * MINIMAL PATCH APPROACH — only patches _barcodeProductAction.
 * Manual search bar handled via a global document keydown listener
 * (no setup(), no updateSearch(), no onMounted — zero lifecycle interference).
 *
 * Features:
 *  - Scan / type package barcode → adds correct qty + price
 *  - Max Combo Limit per bill (blocks scanning beyond the limit)
 */

import { patch }         from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

// ── Barcode map cache ─────────────────────────────────────────────────────────
let _customBarcodeMap = null;
let _fetchPromise     = null;

async function fetchCustomBarcodeMap() {
    if (_customBarcodeMap !== null) return _customBarcodeMap;
    if (_fetchPromise)              return _fetchPromise;
    _fetchPromise = (async () => {
        try {
            const resp = await fetch('/pos/custom_barcode_map', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ jsonrpc: '2.0', method: 'call', params: {} }),
            });
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const json = await resp.json();
            const raw  = (json?.result ?? json)?.barcodes ?? {};
            _customBarcodeMap = {};
            for (const [k, v] of Object.entries(raw))
                _customBarcodeMap[k.toUpperCase()] = v;
            console.log(`[CustomBarcode] ✅ ${Object.keys(_customBarcodeMap).length} barcode(s) loaded:`, Object.keys(_customBarcodeMap));
        } catch (e) {
            console.error('[CustomBarcode] Failed to load barcode map:', e);
            _customBarcodeMap = {};
        }
        return _customBarcodeMap;
    })();
    return _fetchPromise;
}

function findProductById(pos, id) {
    try {
        const m = pos.models?.['product.product'];
        if (!m) return null;
        if (typeof m.getBy === 'function') return m.getBy('id', id) || null;
        if (typeof m.get   === 'function') return m.get(id) || null;
        if (m.records) return m.records[id]
            || Object.values(m.records).find(p => p.id === id) || null;
    } catch(e) {}
    return null;
}

function showNotification(screen, msg, type = 'success') {
    try {
        const svc = screen.env?.services?.notification;
        if (svc) svc.add(msg, { type });
    } catch(e) {}
}

function getCurrentOrder(pos) {
    return pos.get_order?.() || pos.selectedOrder || pos.currentOrder || null;
}

function getLastLine(order) {
    return order?.get_selected_orderline?.()
        || order?.selected_orderline
        || order?.get_orderlines?.()?.at(-1)
        || order?.orderlines?.at?.(-1) || null;
}

function countComboOnOrder(order, entry) {
    if (!order) return 0;
    let lines = [];
    try { lines = order.get_orderlines?.() || order.orderlines || []; } catch(e) { return 0; }
    let count = 0;
    for (const line of lines) {
        const pid = line.product?.id ?? line.product_id?.id ?? line.product_id;
        const qty = line.qty ?? line.quantity ?? 0;
        if (pid === entry.product_id && qty === entry.qty) count++;
    }
    return count;
}

async function applyPrice(order, price) {
    await new Promise(r => setTimeout(r, 150));
    const line = getLastLine(order);
    if (!line) return;
    if (typeof line.set_unit_price === 'function') {
        line.set_unit_price(price);
        await new Promise(r => setTimeout(r, 50));
        line.set_unit_price(price);
    } else if (typeof line.update === 'function') {
        line.update({ price_unit: price, price_manually_set: true });
    } else if ('price_unit' in line) {
        line.price_unit = price;
    }
}

// ── Core handler (used by both scanner and search bar) ────────────────────────
async function handleCustomBarcode(screen, rawBarcode) {
    if (!rawBarcode) return false;
    const map   = await fetchCustomBarcodeMap();
    const entry = map[rawBarcode.toUpperCase()];
    if (!entry) return false;

    const product = findProductById(screen.pos, entry.product_id);
    if (!product) {
        console.warn(`[CustomBarcode] product_id=${entry.product_id} not in POS.`);
        return false;
    }

    // ── Combo limit check ─────────────────────────────────────────────────────
    const maxCombo = entry.max_combo ?? 5;
    if (maxCombo > 0) {
        const comboCount = countComboOnOrder(getCurrentOrder(screen.pos), entry);
        if (comboCount >= maxCombo) {
            showNotification(screen,
                `⚠️ Combo limit reached! "${entry.product_name}" max ${maxCombo}×/bill.`,
                'danger'
            );
            console.warn(`[CustomBarcode] BLOCKED — combo limit ${maxCombo} reached`);
            return true;
        }
    }

    // ── Add product ───────────────────────────────────────────────────────────
    try {
        screen.pos.addLineToCurrentOrder({
            product_id: product,
            qty:        entry.qty,
        }, {
            price_unit:         entry.price,
            price_extra:        0,
            lst_price:          entry.price,
            price_manually_set: true,
        });

        await applyPrice(getCurrentOrder(screen.pos), entry.price);
    } catch (err) {
        console.error('[CustomBarcode] Error adding product:', err);
        return false;
    }

    // ── Success notification ──────────────────────────────────────────────────
    const used      = countComboOnOrder(getCurrentOrder(screen.pos), entry);
    const symbol    = screen.pos.currency?.symbol ?? '₹';
    const remaining = maxCombo > 0 ? ` (${used}/${maxCombo} combos used)` : '';
    showNotification(screen,
        `${entry.product_name}  ×  ${entry.qty}  =  ${symbol}${(entry.qty * entry.price).toFixed(2)}${remaining}`
    );
    screen.numberBuffer?.reset?.();
    return true;
}

// ── Track the active ProductScreen via a simple reference ─────────────────────
// We store the instance each time _barcodeProductAction is called so the
// global keydown handler can use it for manual search bar input.
let _activeScreen = null;

// ── Global keydown listener for manual search bar input ───────────────────────
// Attached once at module load. Safe because it only fires on Enter
// and only acts if the value matches a known barcode.
document.addEventListener('keydown', async (evt) => {
    if (evt.key !== 'Enter') return;
    if (!_activeScreen) return;

    const input = evt.target;
    if (!input || input.tagName !== 'INPUT') return;

    const word = input.value?.trim();
    if (!word) return;

    // Only intercept if it's a known custom barcode
    const map = await fetchCustomBarcodeMap();
    if (!map[word.toUpperCase()]) return;

    console.log('[CustomBarcode] Search Enter intercepted, value:', word);
    evt.preventDefault();
    evt.stopImmediatePropagation();

    const handled = await handleCustomBarcode(_activeScreen, word);
    if (handled) {
        // Clear the input
        try {
            const setter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value'
            )?.set;
            setter?.call(input, '');
            input.dispatchEvent(new Event('input', { bubbles: true }));
        } catch(e) { input.value = ''; }
        try { _activeScreen.updateSearch?.(''); } catch(e) {}
        try { if (_activeScreen.state?.searchWord !== undefined) _activeScreen.state.searchWord = ''; } catch(e) {}
    }
}, true);   // capture phase — runs before Odoo handlers

// ── Patch ProductScreen — ONLY _barcodeProductAction ─────────────────────────
patch(ProductScreen.prototype, {
    async _barcodeProductAction(code) {
        // Keep a reference to the active screen for the global keydown handler
        _activeScreen = this;

        const raw = typeof code === 'string'
            ? code : (code?.code ?? code?.base_code ?? code?.value ?? '');
        if (raw && await handleCustomBarcode(this, raw)) return;
        return super._barcodeProductAction(code);
    },
});

// Pre-warm the barcode cache
fetchCustomBarcodeMap().catch(() => {});
console.log('[CustomBarcode] ✅ v26 loaded — Max Combo Limit active.');
