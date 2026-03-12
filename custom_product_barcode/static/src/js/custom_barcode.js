/** @odoo-module */
/**
 * custom_barcode.js  –  Odoo 19 CE
 * Place at: custom_product_barcode/static/src/js/custom_barcode.js
 */

import { patch }         from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { onMounted, onWillUnmount } from "@odoo/owl";

console.log('[CustomBarcode] ✅ Module loading...');

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
            console.log(`[CustomBarcode] ✅ ${Object.keys(_customBarcodeMap).length} barcode(s) loaded`, Object.keys(_customBarcodeMap));
        } catch (e) {
            console.error('[CustomBarcode] ❌ Failed to load barcode map:', e);
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
    } catch(e) {}
}

function getCurrentOrder(pos) {
    return pos.get_order?.() || pos.selectedOrder || pos.currentOrder || null;
}

function getLastLine(order) {
    const lines = order?.get_orderlines?.() || order?.orderlines || [];
    const arr   = Array.isArray(lines) ? lines : (lines.toArray?.() ?? [...lines]);
    return arr.at(-1) || null;
}

// ── Dedup guard ───────────────────────────────────────────────────────────────
const _recentlySeen = new Map();
function isDuplicate(key) {
    const now  = Date.now();
    const last = _recentlySeen.get(key);
    if (last && (now - last) < 1500) return true;
    _recentlySeen.set(key, now);
    for (const [k, t] of _recentlySeen) if (now - t > 5000) _recentlySeen.delete(k);
    return false;
}

// ── Force price + qty on a line ───────────────────────────────────────────────
function applyToLine(line, qty, price) {
    if (!line) return;
    line.price_manually_set = true;

    // Qty
    if (typeof line.set_quantity  === 'function') try { line.set_quantity(qty);  } catch(e) {}
    else if (typeof line.setQuantity === 'function') try { line.setQuantity(qty); } catch(e) {}
    else { try { line.qty = qty;      } catch(e) {} }

    // Price
    if (typeof line.set_unit_price === 'function') try { line.set_unit_price(price); } catch(e) {}
    else if (typeof line.setUnitPrice === 'function') try { line.setUnitPrice(price); } catch(e) {}

    // Also direct assign + update() for reactive models
    try { line.price_unit = price; } catch(e) {}
    if (typeof line.update === 'function') {
        try { line.update({ price_unit: price, price_manually_set: true }); } catch(e) {}
    }
}

async function handleCustomBarcode(screen, rawBarcode) {
    if (!rawBarcode) return false;
    const key = rawBarcode.trim().toUpperCase();

    if (isDuplicate(key)) return true;

    const map   = await fetchCustomBarcodeMap();
    const entry = map[key];
    if (!entry) {
        _recentlySeen.delete(key);
        return false;
    }

    const product = findProductById(screen.pos, entry.product_id);
    if (!product) {
        console.warn(`[CustomBarcode] ❌ product id=${entry.product_id} not in POS`);
        _recentlySeen.delete(key);
        return false;
    }

    console.log(`[CustomBarcode] Matched: ${entry.product_name}  qty=${entry.qty}  price=${entry.price}`);

    try {
        const order = getCurrentOrder(screen.pos);
        if (!order) throw new Error('No active order');

        screen.pos.addLineToCurrentOrder(
            { product_id: product },
            { price_manually_set: true }
        );

        // Apply immediately
        applyToLine(getLastLine(order), entry.qty, entry.price);

        // Re-apply at intervals to beat async pricelist hooks
        for (const ms of [30, 100, 300, 700, 1500]) {
            await new Promise(r => setTimeout(r, ms));
            const line = getLastLine(order);
            if (!line) continue;
            const curPrice = line.price_unit;
            const curQty   = line.qty ?? line.quantity;
            if (Math.abs(curPrice - entry.price) > 0.001 || Math.abs(curQty - entry.qty) > 0.001) {
                console.log(`[CustomBarcode] Re-applying at ${ms}ms — price was ${curPrice}, qty was ${curQty}`);
                applyToLine(line, entry.qty, entry.price);
            }
        }

    } catch (err) {
        console.error('[CustomBarcode] Error:', err);
        return false;
    }

    const sym = screen.pos.currency?.symbol ?? '₹';
    showNotification(screen,
        `${entry.product_name} × ${entry.qty} @ ${sym}${entry.price.toFixed(2)} = ${sym}${(entry.qty * entry.price).toFixed(2)}`
    );
    screen.numberBuffer?.reset?.();
    return true;
}

// ── Search input helpers ──────────────────────────────────────────────────────
const SEARCH_SELECTORS = [
    'input[placeholder*="earch"]',
    '.search-bar input',
    '.pos-search-bar input',
    '.product-screen input[type="text"]',
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
                const handled = await handleCustomBarcode(this, word);
                if (handled) {
                    evt.preventDefault();
                    evt.stopImmediatePropagation();
                    try {
                        const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
                        setter?.set?.call(input, '');
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                    } catch(e) { input.value = ''; }
                    try { this.updateSearch?.(''); } catch(e) {}
                    try { if (this.state?.searchWord !== undefined) this.state.searchWord = ''; } catch(e) {}
                }
            };
            input.addEventListener('keydown', _keyHandler, true);
        };

        onMounted(() => {
            attachToInput(findSearchInput());
            _observer = new MutationObserver(() => {
                const n = findSearchInput();
                if (n && n !== _currentInput) attachToInput(n);
            });
            _observer.observe(document.body, { childList: true, subtree: true });
        });

        onWillUnmount(() => {
            if (_currentInput && _keyHandler)
                _currentInput.removeEventListener('keydown', _keyHandler, true);
            _observer?.disconnect();
        });
    },

    async _barcodeProductAction(code) {
        const raw = typeof code === 'string'
            ? code : (code?.code ?? code?.base_code ?? code?.value ?? '');
        if (raw && await handleCustomBarcode(this, raw)) return;
        return super._barcodeProductAction(code);
    },
});

console.log('[CustomBarcode] ✅ Patch applied to ProductScreen');