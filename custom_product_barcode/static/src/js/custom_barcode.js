/** @odoo-module */
/**
 * custom_barcode.js  –  Odoo 19 CE
 *
 * Fixes:
 *  1. Duplicate handling (3x notifications) — global 1-second dedup lock
 *  2. Price not applied — set_unit_price after line creation + re-apply after async hooks
 */

import { patch }         from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { onMounted, onWillUnmount } from "@odoo/owl";

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
            console.log(`[CustomBarcode] loaded ${Object.keys(_customBarcodeMap).length} barcode(s)`);
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

function showNotification(screen, msg) {
    try {
        const svc = screen.env?.services?.notification;
        if (svc) svc.add(msg, { type: 'success' });
        else if (screen.notification) screen.notification.add(msg, { type: 'success' });
    } catch(e) {}
}

function getCurrentOrder(pos) {
    return pos.get_order?.() || pos.selectedOrder || pos.currentOrder || null;
}

function getLastLine(order) {
    const lines = order?.get_orderlines?.() || order?.orderlines || [];
    const arr = Array.isArray(lines) ? lines : (lines.toArray?.() ?? [...lines]);
    return arr.at(-1) || null;
}

// ── Global dedup lock: prevents same barcode firing twice within 1 second ─────
const _recentlySeen = new Map();

function isDuplicate(key) {
    const now  = Date.now();
    const last = _recentlySeen.get(key);
    if (last && (now - last) < 1000) {
        console.log(`[CustomBarcode] Suppressed duplicate "${key}" (${now - last}ms ago)`);
        return true;
    }
    _recentlySeen.set(key, now);
    // Clean old entries
    for (const [k, t] of _recentlySeen) if (now - t > 5000) _recentlySeen.delete(k);
    return false;
}

// ── Apply price + qty to an orderline ────────────────────────────────────────
function applyToLine(line, qty, price) {
    if (!line) return;

    // Mark price as manually set — blocks Odoo's async pricelist from overwriting
    line.price_manually_set = true;

    // Set qty
    if (Math.abs((line.qty ?? line.quantity ?? 0) - qty) > 0.001) {
        if      (typeof line.set_quantity  === 'function') line.set_quantity(qty);
        else if (typeof line.setQuantity   === 'function') line.setQuantity(qty);
        else if (typeof line.update        === 'function') line.update({ qty });
        else line.qty = qty;
    }

    // Set price via every known method
    if (typeof line.set_unit_price === 'function') line.set_unit_price(price);
    if (typeof line.setUnitPrice   === 'function') line.setUnitPrice(price);
    if (typeof line.update === 'function') {
        try { line.update({ price_unit: price, price_manually_set: true }); } catch(e) {}
    }
    line.price_unit = price;

    console.log(`[CustomBarcode] applyToLine → qty=${line.qty ?? line.quantity}  price_unit=${line.price_unit}`);
}

async function handleCustomBarcode(screen, rawBarcode) {
    if (!rawBarcode) return false;
    const key = rawBarcode.trim().toUpperCase();

    // ── Dedup guard ───────────────────────────────────────────────────────────
    if (isDuplicate(key)) return true; // true = "handled", stops fallthrough

    const map   = await fetchCustomBarcodeMap();
    const entry = map[key];
    if (!entry) {
        // Not our barcode — remove the timestamp so normal flow can proceed
        _recentlySeen.delete(key);
        return false;
    }

    const product = findProductById(screen.pos, entry.product_id);
    if (!product) {
        console.warn(`[CustomBarcode] product id=${entry.product_id} not found in POS`);
        _recentlySeen.delete(key);
        return false;
    }

    console.log(`[CustomBarcode] → ${entry.product_name}  qty=${entry.qty}  price=${entry.price}`);

    try {
        const order = getCurrentOrder(screen.pos);
        if (!order) throw new Error('No active order');

        // Add the line — we don't rely on price from here
        screen.pos.addLineToCurrentOrder(
            { product_id: product },
            { price_manually_set: true }
        );

        // Apply qty + price immediately (synchronous)
        applyToLine(getLastLine(order), entry.qty, entry.price);

        // Re-apply after Odoo's async pricelist/tax hooks settle
        await new Promise(r => setTimeout(r, 60));
        applyToLine(getLastLine(order), entry.qty, entry.price);

        await new Promise(r => setTimeout(r, 250));
        applyToLine(getLastLine(order), entry.qty, entry.price);

    } catch (err) {
        console.error('[CustomBarcode] Error adding product:', err);
        return false;
    }

    const sym = screen.pos.currency?.symbol ?? '₹';
    showNotification(screen,
        `${entry.product_name} × ${entry.qty} @ ${sym}${entry.price.toFixed(2)} = ${sym}${(entry.qty * entry.price).toFixed(2)}`
    );
    screen.numberBuffer?.reset?.();
    return true;
}

// ── Search input selectors ────────────────────────────────────────────────────
const SEARCH_SELECTORS = [
    'input[placeholder*="earch"]',
    '.search-bar input',
    '.pos-search-bar input',
    '.product-screen input[type="text"]',
    '.pos input[type="text"]',
];

function findSearchInput() {
    for (const sel of SEARCH_SELECTORS) {
        const el = document.querySelector(sel);
        if (el) return el;
    }
    return null;
}

// ── Patch ProductScreen ───────────────────────────────────────────────────────
patch(ProductScreen.prototype, {

    setup() {
        super.setup();
        fetchCustomBarcodeMap().catch(() => {});

        let _currentInput = null;
        let _keyHandler   = null;
        let _observer     = null;

        const attachToInput = (input) => {
            if (!input || input === _currentInput) return;
            if (_currentInput && _keyHandler)
                _currentInput.removeEventListener('keydown', _keyHandler, true);

            _currentInput = input;
            _keyHandler = async (evt) => {
                if (evt.key !== 'Enter') return;
                const word = input.value?.trim();
                if (!word) return;
                console.log('[CustomBarcode] Search Enter:', JSON.stringify(word));
                const handled = await handleCustomBarcode(this, word);
                if (handled) {
                    evt.preventDefault();
                    evt.stopImmediatePropagation();
                    // Clear the input
                    try {
                        const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
                        setter?.set?.call(input, '');
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                    } catch(e) { input.value = ''; }
                    try { this.updateSearch?.(''); }      catch(e) {}
                    try { if (this.state?.searchWord !== undefined) this.state.searchWord = ''; } catch(e) {}
                }
            };
            input.addEventListener('keydown', _keyHandler, true);
            console.log('[CustomBarcode] ✅ Attached to search input');
        };

        onMounted(() => {
            const input = findSearchInput();
            if (input) attachToInput(input);

            _observer = new MutationObserver(() => {
                const newInput = findSearchInput();
                if (newInput && newInput !== _currentInput) attachToInput(newInput);
            });
            _observer.observe(document.body, { childList: true, subtree: true });
        });

        onWillUnmount(() => {
            if (_currentInput && _keyHandler)
                _currentInput.removeEventListener('keydown', _keyHandler, true);
            _observer?.disconnect();
        });
    },

    // ── Physical barcode scanner ──────────────────────────────────────────────
    async _barcodeProductAction(code) {
        const raw = typeof code === 'string'
            ? code : (code?.code ?? code?.base_code ?? code?.value ?? '');
        console.log('[CustomBarcode] _barcodeProductAction:', JSON.stringify(raw));
        if (raw && await handleCustomBarcode(this, raw)) return;
        return super._barcodeProductAction(code);
    },
});

console.log('[CustomBarcode] ✅ v19 — dedup guard + price fix active.');