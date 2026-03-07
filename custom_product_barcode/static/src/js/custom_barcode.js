/** @odoo-module */
/**
 * custom_barcode.js  –  Odoo 19 CE  (v17)
 *
 * Handles BOTH:
 *   1. Barcode scanner  → _barcodeProductAction (existing patch)
 *   2. Manual typing in POS search bar + Enter → new patch on search confirm
 *
 * When the typed search term exactly matches a custom barcode (case-insensitive),
 * the product is added with the correct package qty & price instead of
 * showing "No products found".
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
            console.log(`[CustomBarcode] ✅ ${Object.keys(_customBarcodeMap).length} package barcode(s) loaded.`);
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

function forcePriceOnLine(order, unitPrice) {
    const line = order?.get_selected_orderline?.()
              || order?.selected_orderline
              || order?.get_orderlines?.()?.at(-1)
              || order?.orderlines?.at?.(-1) || null;
    if (!line) return;
    if (typeof line.set_unit_price === 'function') { line.set_unit_price(unitPrice); return; }
    if (typeof line.setUnitPrice   === 'function') { line.setUnitPrice(unitPrice);   return; }
    if ('price_unit' in line) line.price_unit = unitPrice;
}

// ── Core: add product with package qty + price ────────────────────────────────
async function handleCustomBarcode(screen, barcodeStr) {
    const map   = await fetchCustomBarcodeMap();
    const entry = map[barcodeStr.toUpperCase()];
    if (!entry) return false;   // not a custom barcode

    const product = findProductById(screen.pos, entry.product_id);
    if (!product) {
        console.warn(`[CustomBarcode] product_id=${entry.product_id} not in POS — enable in POS config.`);
        return false;
    }

    try {
        screen.pos.addLineToCurrentOrder({
            product_id: product,
            qty:        entry.qty,
            price_unit: entry.price,
        });

        await new Promise(r => setTimeout(r, 40));
        const order = getCurrentOrder(screen.pos);
        forcePriceOnLine(order, entry.price);
    } catch (err) {
        console.error('[CustomBarcode] Error adding product:', err);
        return false;
    }

    const symbol = screen.pos.currency?.symbol ?? '₹';
    showNotification(screen,
        `${entry.product_name}  ×  ${entry.qty}  =  ${symbol}${(entry.qty * entry.price).toFixed(2)}`
    );
    screen.numberBuffer?.reset?.();
    return true;   // handled
}

// ── Patch ProductScreen ───────────────────────────────────────────────────────
patch(ProductScreen.prototype, {

    // ── 1. Barcode scanner path ───────────────────────────────────────────────
    async _barcodeProductAction(code) {
        const raw = typeof code === 'string'
            ? code : (code?.code ?? code?.base_code ?? code?.value ?? '');

        if (raw && await handleCustomBarcode(this, raw)) return;
        return super._barcodeProductAction(code);
    },

    // ── 2. Manual search bar path (user types + presses Enter) ───────────────
    // Odoo 19 calls updateSearch(searchWord) when search bar value changes.
    // When the user confirms (Enter / barcode-like string), it also calls
    // _barcodeProductAction — but ONLY if the POS thinks it looks like a
    // barcode. If not, it falls through to product search.
    //
    // We intercept at the search-confirmation level.
    // Odoo 19 uses onSearch prop passed to SearchBar; ProductScreen handles it
    // via its own search state. The exact method varies:
    //   - updateSearch(val)        — called on every keystroke
    //   - _onSearch(val) or        — called on Enter/confirm
    //   - _searchProduct(val)
    //
    // We patch ALL of them for maximum compatibility.

    updateSearch(searchWord) {
        // Store the last typed value so we can check it on Enter
        this._lastSearchWord = searchWord;
        return super.updateSearch(searchWord);
    },

    // Called when user presses Enter in the search bar in some Odoo 19 builds
    async _onSearch(searchWord) {
        const word = searchWord ?? this._lastSearchWord ?? '';
        if (word && await handleCustomBarcode(this, word)) {
            // Clear the search bar
            try { this.updateSearch(''); } catch(e) {}
            return;
        }
        return super._onSearch?.(searchWord);
    },

    // Alternative name used in some Odoo 19 builds
    async _searchProduct(searchWord) {
        const word = searchWord ?? this._lastSearchWord ?? '';
        if (word && await handleCustomBarcode(this, word)) {
            try { this.updateSearch(''); } catch(e) {}
            return;
        }
        return super._searchProduct?.(searchWord);
    },
});

// ── Also intercept the SearchBar keydown at DOM level (ultimate fallback) ─────
// If the above patches don't catch it, we listen for Enter on the search input.
document.addEventListener('keydown', async (evt) => {
    if (evt.key !== 'Enter') return;

    const input = evt.target;
    if (!input || input.tagName !== 'INPUT') return;

    // Only act on the POS search bar (has class or placeholder related to search)
    const isSearchBar = input.closest?.('.search-bar, .pos-search-bar, [class*="search"]');
    if (!isSearchBar) return;

    const word = input.value?.trim();
    if (!word) return;

    // Check if this matches a custom barcode
    const map = await fetchCustomBarcodeMap();
    if (!map[word.toUpperCase()]) return;   // not our barcode, let POS handle it

    // Prevent POS from also handling it (showing "no products found")
    evt.stopImmediatePropagation();

    // Find the active ProductScreen instance via Owl's global registry
    // We look for the POS environment on the root app
    try {
        const posApp = document.querySelector('.pos, #pos-content, .point-of-sale');
        if (!posApp?.__owl__) return;

        // Walk up the Owl component tree to find ProductScreen
        function findComponent(node, name) {
            if (!node) return null;
            if (node.component?.constructor?.name === name) return node.component;
            for (const child of Object.values(node.children || {})) {
                const found = findComponent(child, name);
                if (found) return found;
            }
            return null;
        }

        const screen = findComponent(posApp.__owl__, 'ProductScreen');
        if (screen) {
            const handled = await handleCustomBarcode(screen, word);
            if (handled) {
                input.value = '';
                // Trigger input event to clear the search display
                input.dispatchEvent(new Event('input', { bubbles: true }));
            }
        }
    } catch(e) {
        console.warn('[CustomBarcode] DOM fallback error:', e.message);
    }
}, true);  // capture phase — runs before POS handlers

fetchCustomBarcodeMap().catch(() => {});
console.log('[CustomBarcode] ✅ v17 loaded — scanner + manual search both handled.');
