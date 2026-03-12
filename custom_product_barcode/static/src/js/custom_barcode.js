/** @odoo-module */
/**
 * custom_barcode.js  –  Odoo 19 CE  (v22 — Max Combo Limit)
 *
 * NEW: Max Combo Limit per bill.
 *   - Each package barcode has a max_combo field (default 5).
 *   - The JS counts how many times that barcode's product+qty already appears
 *     on the current order lines.
 *   - If the count >= max_combo, show a warning and BLOCK the scan.
 *   - max_combo = 0 means unlimited.
 *
 * Handles BOTH physical scanner and manual search bar typing.
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
        else if (screen.notification) screen.notification.add(msg, { type });
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

// ── Count how many times this barcode's package has been added this bill ──────
function countComboOnOrder(order, entry) {
    if (!order) return 0;
    let lines = [];
    try {
        lines = order.get_orderlines?.() || order.orderlines || [];
    } catch(e) { return 0; }

    let count = 0;
    for (const line of lines) {
        const lineProductId = line.product?.id ?? line.product_id?.id ?? line.product_id;
        const lineQty       = line.qty ?? line.quantity ?? 0;
        // Count lines that match this barcode's product AND package qty
        if (lineProductId === entry.product_id && lineQty === entry.qty) {
            count++;
        }
    }
    return count;
}

// ── Set price on order line after Odoo's post-add hooks ──────────────────────
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

// ── Core handler ──────────────────────────────────────────────────────────────
async function handleCustomBarcode(screen, rawBarcode) {
    if (!rawBarcode) return false;
    const map   = await fetchCustomBarcodeMap();
    const entry = map[rawBarcode.toUpperCase()];
    if (!entry) return false;

    const product = findProductById(screen.pos, entry.product_id);
    if (!product) {
        console.warn(`[CustomBarcode] product_id=${entry.product_id} not in POS — enable in POS config.`);
        return false;
    }

    // ── Check max combo limit ─────────────────────────────────────────────────
    const maxCombo = entry.max_combo ?? 5;   // default 5 if server didn't send it
    if (maxCombo > 0) {
        const order      = getCurrentOrder(screen.pos);
        const comboCount = countComboOnOrder(order, entry);
        console.log(`[CustomBarcode] Combo count for ${rawBarcode}: ${comboCount} / ${maxCombo}`);

        if (comboCount >= maxCombo) {
            // BLOCKED — show warning notification
            showNotification(
                screen,
                `⚠️ Maximum combo limit reached! "${entry.product_name}" package can only be added ${maxCombo} time(s) per bill.`,
                'danger'
            );
            console.warn(`[CustomBarcode] BLOCKED — combo limit ${maxCombo} reached for ${rawBarcode}`);
            return true;   // return true so we don't fall through to default POS handler
        }
    }

    // ── Add the line ──────────────────────────────────────────────────────────
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

        const order = getCurrentOrder(screen.pos);
        await applyPrice(order, entry.price);

    } catch (err) {
        console.error('[CustomBarcode] Error adding product:', err);
        return false;
    }

    // ── Success notification with remaining combos ─────────────────────────────
    const order      = getCurrentOrder(screen.pos);
    const used       = countComboOnOrder(order, entry);
    const maxCombo   = entry.max_combo ?? 5;
    const symbol     = screen.pos.currency?.symbol ?? '₹';
    const remaining  = maxCombo > 0 ? ` (${used}/${maxCombo} combos used)` : '';

    showNotification(
        screen,
        `${entry.product_name}  ×  ${entry.qty}  =  ${symbol}${(entry.qty * entry.price).toFixed(2)}${remaining}`,
        'success'
    );
    screen.numberBuffer?.reset?.();
    return true;
}

// ── Search input selectors ─────────────────────────────────────────────────────
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
            if (_currentInput && _keyHandler) {
                _currentInput.removeEventListener('keydown', _keyHandler, true);
            }
            _currentInput = input;
            _keyHandler = async (evt) => {
                if (evt.key !== 'Enter') return;
                const word = input.value?.trim();
                if (!word) return;

                console.log('[CustomBarcode] Search Enter pressed, value:', word);
                const handled = await handleCustomBarcode(this, word);
                if (handled) {
                    evt.preventDefault();
                    evt.stopImmediatePropagation();
                    try {
                        const nativeSet = Object.getOwnPropertyDescriptor(
                            window.HTMLInputElement.prototype, 'value'
                        )?.set;
                        nativeSet?.call(input, '');
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                    } catch(e) { input.value = ''; }
                    try { this.updateSearch?.(''); } catch(e) {}
                    try { if (this.state?.searchWord !== undefined) this.state.searchWord = ''; } catch(e) {}
                }
            };
            input.addEventListener('keydown', _keyHandler, true);
            console.log('[CustomBarcode] ✅ Attached keydown listener to search input');
        };

        onMounted(() => {
            const input = findSearchInput();
            if (input) attachToInput(input);

            _observer = new MutationObserver(() => {
                const newInput = findSearchInput();
                if (newInput && newInput !== _currentInput) {
                    attachToInput(newInput);
                }
            });
            _observer.observe(document.body, { childList: true, subtree: true });
        });

        onWillUnmount(() => {
            if (_currentInput && _keyHandler) {
                _currentInput.removeEventListener('keydown', _keyHandler, true);
            }
            _observer?.disconnect();
        });
    },

    // ── Physical barcode scanner ──────────────────────────────────────────────
    async _barcodeProductAction(code) {
        const raw = typeof code === 'string'
            ? code : (code?.code ?? code?.base_code ?? code?.value ?? '');
        if (raw && await handleCustomBarcode(this, raw)) return;
        return super._barcodeProductAction(code);
    },
});

console.log('[CustomBarcode] ✅ v22 loaded — Max Combo Limit active.');
