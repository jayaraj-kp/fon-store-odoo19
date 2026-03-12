/** @odoo-module */
/**
 * custom_barcode.js  –  Odoo 19 CE  (v19)
 *
 * Fix: Price was being reset by Odoo's async pricelist computation after addLineToCurrentOrder.
 * Solution: Directly manipulate the order line AFTER it's created, and use
 *           price_manually_set=true + override the getUnitPrice method on the line instance
 *           to always return our custom price, preventing pricelist from overwriting it.
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
    // Try selected line first, then last line
    const lines = order?.get_orderlines?.() || order?.orderlines || [];
    const arr = Array.isArray(lines) ? lines : (lines.toArray?.() ?? [...lines]);
    return order?.get_selected_orderline?.()
        || order?.selected_orderline
        || arr.at(-1)
        || null;
}

/**
 * Force-set price on a line using every available method.
 * Also monkey-patches getUnitPrice on the instance so pricelist
 * cannot overwrite it asynchronously.
 */
function forcePrice(line, price) {
    if (!line) return;

    // 1. Mark as manually set first — prevents pricelist override
    if ('price_manually_set' in line) line.price_manually_set = true;
    if (typeof line.update === 'function') {
        try { line.update({ price_manually_set: true }); } catch(e) {}
    }

    // 2. Monkey-patch getUnitPrice on THIS instance so async pricelist
    //    computations always return our price (Odoo 19 reactive pattern)
    try {
        line._customForcedPrice = price;
        const originalGetUnitPrice = line.getUnitPrice?.bind(line);
        line.getUnitPrice = function() { return this._customForcedPrice; };
        // Also patch get_unit_price (Odoo 16/17/18 name)
        line.get_unit_price = function() { return this._customForcedPrice; };
    } catch(e) {}

    // 3. Set via all known setter methods
    if (typeof line.set_unit_price === 'function') {
        try { line.set_unit_price(price); } catch(e) {}
    }
    if (typeof line.setUnitPrice === 'function') {
        try { line.setUnitPrice(price); } catch(e) {}
    }
    if (typeof line.update === 'function') {
        try { line.update({ price_unit: price, lst_price: price }); } catch(e) {}
    }

    // 4. Direct property assignment as final guarantee
    try { line.price_unit = price; } catch(e) {}
    try { line.lst_price  = price; } catch(e) {}

    console.log(`[CustomBarcode] forcePrice(${price}) → price_unit now:`, line.price_unit);
}

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

    console.log(`[CustomBarcode] Handling barcode for ${entry.product_name}, qty=${entry.qty}, price=${entry.price}`);

    try {
        const order = getCurrentOrder(screen.pos);
        if (!order) throw new Error('No active order');

        // ── Strategy: add line then immediately and repeatedly override price ──
        //
        // Odoo 19 calls an async pricelist RPC after addLineToCurrentOrder.
        // We beat it by:
        //   a) Passing price_unit in the vals (may or may not work depending on version)
        //   b) Setting price_manually_set=true so Odoo skips pricelist update
        //   c) Overriding getUnitPrice on the line instance
        //   d) Setting price again after short delays to catch any late resets

        screen.pos.addLineToCurrentOrder(
            { product_id: product },
            {
                qty:                entry.qty,
                price_unit:         entry.price,
                lst_price:          entry.price,
                price_manually_set: true,
            }
        );

        // Immediately grab the line and force price — before any async hooks
        const lineImmediate = getLastLine(order);
        if (lineImmediate) {
            forcePrice(lineImmediate, entry.price);
            // Also set qty immediately in case addLineToCurrentOrder ignored it
            if (typeof lineImmediate.set_quantity === 'function') {
                try { lineImmediate.set_quantity(entry.qty); } catch(e) {}
            } else if (typeof lineImmediate.setQuantity === 'function') {
                try { lineImmediate.setQuantity(entry.qty); } catch(e) {}
            } else if (typeof lineImmediate.update === 'function') {
                try { lineImmediate.update({ qty: entry.qty }); } catch(e) {}
            }
        }

        // Re-apply after short delays to catch Odoo's async pricelist reset
        // Odoo 19 typically fires pricelist update at ~0ms, ~30ms, ~100ms
        for (const delay of [0, 30, 80, 200, 500]) {
            await new Promise(r => setTimeout(r, delay));
            const line = getLastLine(order);
            if (!line) continue;
            // Only re-apply if price was reset away from our value
            const currentPrice = line.price_unit ?? line.price;
            if (Math.abs(currentPrice - entry.price) > 0.001) {
                console.log(`[CustomBarcode] Price was reset to ${currentPrice} at ${delay}ms — correcting back to ${entry.price}`);
                forcePrice(line, entry.price);
            }
        }

    } catch (err) {
        console.error('[CustomBarcode] Error adding product:', err);
        return false;
    }

    const symbol = screen.pos.currency?.symbol ?? '₹';
    showNotification(screen,
        `${entry.product_name}  ×  ${entry.qty}  @  ${symbol}${entry.price.toFixed(2)}  =  ${symbol}${(entry.qty * entry.price).toFixed(2)}`
    );
    screen.numberBuffer?.reset?.();
    return true;
}

// ── Search input selectors to try ─────────────────────────────────────────────
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

        let _currentInput   = null;
        let _keyHandler     = null;
        let _observer       = null;

        const attachToInput = (input) => {
            if (!input || input === _currentInput) return;
            if (_currentInput && _keyHandler) {
                _currentInput.removeEventListener('keydown', _keyHandler, true);
                console.log('[CustomBarcode] Detached from old input');
            }
            _currentInput = input;
            _keyHandler = async (evt) => {
                if (evt.key !== 'Enter') return;
                const word = input.value?.trim();
                console.log('[CustomBarcode] Search Enter pressed, value:', JSON.stringify(word));
                if (!word) return;

                const handled = await handleCustomBarcode(this, word);
                console.log('[CustomBarcode] handleCustomBarcode result:', handled);
                if (handled) {
                    evt.preventDefault();
                    evt.stopImmediatePropagation();
                    // Clear search input and internal state
                    try {
                        const nativeInput = Object.getOwnPropertyDescriptor(
                            window.HTMLInputElement.prototype, 'value'
                        );
                        nativeInput?.set?.call(input, '');
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
                    console.log('[CustomBarcode] Input element replaced — re-attaching listener');
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
        console.log('[CustomBarcode] _barcodeProductAction called with:', JSON.stringify(raw));
        if (raw && await handleCustomBarcode(this, raw)) return;
        return super._barcodeProductAction(code);
    },
});

console.log('[CustomBarcode] ✅ v19 loaded — price override with pricelist-bypass active.');