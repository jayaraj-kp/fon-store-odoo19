/** @odoo-module */
/**
 * custom_barcode.js  –  Odoo 19 CE
 *
 * Root cause of price not sticking:
 *   Odoo 19 calls an async RPC (get_price_unit / _computePrice) on the orderline
 *   AFTER the line is created. This fires at ~300-800ms and resets price_unit
 *   back to the pricelist price — overwriting any value we set.
 *
 * Fix:
 *   After adding the line, we use Object.defineProperty() to make price_unit
 *   a locked property on that specific line instance. The async RPC result is
 *   then silently ignored because the property setter rejects it.
 *   We do the same for qty / quantity.
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
            console.error('[CustomBarcode] Failed to load:', e);
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
    const arr   = Array.isArray(lines) ? lines : (lines.toArray?.() ?? [...lines]);
    return arr.at(-1) || null;
}

// ── Global dedup — prevents same barcode firing twice within 1 second ─────────
const _recentlySeen = new Map();
function isDuplicate(key) {
    const now  = Date.now();
    const last = _recentlySeen.get(key);
    if (last && (now - last) < 1000) {
        console.log(`[CustomBarcode] Duplicate suppressed "${key}" (${now - last}ms ago)`);
        return true;
    }
    _recentlySeen.set(key, now);
    for (const [k, t] of _recentlySeen) if (now - t > 5000) _recentlySeen.delete(k);
    return false;
}

/**
 * Lock price_unit and qty on a specific orderline instance using
 * Object.defineProperty so Odoo's async pricelist RPC cannot overwrite them.
 */
function lockLineValues(line, qty, price) {
    if (!line) return;

    console.log('[CustomBarcode] Locking line — before:', {
        qty:        line.qty,
        quantity:   line.quantity,
        price_unit: line.price_unit,
    });

    // ── Lock price_unit ───────────────────────────────────────────────────────
    let _price = price;
    try {
        // Delete the existing property first (may be on prototype or own)
        delete line.price_unit;
        Object.defineProperty(line, 'price_unit', {
            get: ()      => _price,
            set: (v)     => {
                // Allow our own sets (called from this function).
                // Reject anything that tries to set a different value.
                if (Math.abs(v - _price) > 0.001) {
                    console.log(`[CustomBarcode] Blocked price_unit reset: ${v} → keeping ${_price}`);
                } else {
                    _price = v;
                }
            },
            configurable: true,
            enumerable:   true,
        });
    } catch(e) {
        console.warn('[CustomBarcode] defineProperty price_unit failed:', e);
        line.price_unit = price;
    }

    // Also override method-based getters used by Odoo 19
    try { line.getUnitPrice    = () => price; } catch(e) {}
    try { line.get_unit_price  = () => price; } catch(e) {}
    try { line.getDisplayPrice = () => price; } catch(e) {}

    // Prevent pricelist from overwriting by marking as manually set
    line.price_manually_set = true;
    try { line.update?.({ price_manually_set: true }); } catch(e) {}

    // ── Lock qty ─────────────────────────────────────────────────────────────
    let _qty = qty;
    const lockQtyProp = (prop) => {
        try {
            delete line[prop];
            Object.defineProperty(line, prop, {
                get: ()  => _qty,
                set: (v) => {
                    if (Math.abs(v - _qty) > 0.001)
                        console.log(`[CustomBarcode] Blocked ${prop} reset: ${v} → keeping ${_qty}`);
                    else _qty = v;
                },
                configurable: true,
                enumerable:   true,
            });
        } catch(e) {
            line[prop] = qty;
        }
    };
    lockQtyProp('qty');
    lockQtyProp('quantity');

    // Also call setter methods so the UI re-renders immediately
    if (typeof line.set_quantity  === 'function') { try { line.set_quantity(qty);   } catch(e){} }
    if (typeof line.setQuantity   === 'function') { try { line.setQuantity(qty);    } catch(e){} }
    if (typeof line.set_unit_price=== 'function') { try { line.set_unit_price(price); } catch(e){} }
    if (typeof line.setUnitPrice  === 'function') { try { line.setUnitPrice(price);   } catch(e){} }

    console.log('[CustomBarcode] Locked line — after:', {
        qty:        line.qty,
        quantity:   line.quantity,
        price_unit: line.price_unit,
    });
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
        console.warn(`[CustomBarcode] product id=${entry.product_id} not in POS`);
        _recentlySeen.delete(key);
        return false;
    }

    console.log(`[CustomBarcode] → ${entry.product_name}  qty=${entry.qty}  price=${entry.price}`);

    try {
        const order = getCurrentOrder(screen.pos);
        if (!order) throw new Error('No active order');

        // Count lines before adding so we can identify the new line
        const linesBefore = (order?.get_orderlines?.() || order?.orderlines || []);
        const countBefore = Array.isArray(linesBefore)
            ? linesBefore.length
            : (linesBefore.toArray?.() ?? [...linesBefore]).length;

        // Add the line — don't rely on price/qty from here
        screen.pos.addLineToCurrentOrder(
            { product_id: product },
            { price_manually_set: true }
        );

        // Grab and lock the new line immediately (synchronous)
        const line = getLastLine(order);
        if (line) lockLineValues(line, entry.qty, entry.price);

        // Re-lock after Odoo's sync post-processing
        await new Promise(r => setTimeout(r, 20));
        const line2 = getLastLine(order);
        if (line2) lockLineValues(line2, entry.qty, entry.price);

        // Re-lock after async RPC (pricelist) settles — typically 300-600ms
        await new Promise(r => setTimeout(r, 400));
        const line3 = getLastLine(order);
        if (line3) lockLineValues(line3, entry.qty, entry.price);

        await new Promise(r => setTimeout(r, 600));
        const line4 = getLastLine(order);
        if (line4) lockLineValues(line4, entry.qty, entry.price);

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

    async _barcodeProductAction(code) {
        const raw = typeof code === 'string'
            ? code : (code?.code ?? code?.base_code ?? code?.value ?? '');
        console.log('[CustomBarcode] _barcodeProductAction:', JSON.stringify(raw));
        if (raw && await handleCustomBarcode(this, raw)) return;
        return super._barcodeProductAction(code);
    },
});

console.log('[CustomBarcode] ✅ v19 — instance-level price/qty lock active.');
