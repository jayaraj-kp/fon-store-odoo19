/** @odoo-module */
/**
 * custom_barcode.js  –  Odoo 19 CE  (v18)
 *
 * APPROACH: Patch ProductScreen.setup() to attach a keydown listener
 * directly on the search input element via the component's ref.
 * This fires BEFORE Odoo's own handlers and intercepts Enter on custom barcodes.
 *
 * Also patches _barcodeProductAction for physical scanner input.
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

    try {
        screen.pos.addLineToCurrentOrder({
            product_id: product,
            qty:        entry.qty,
            price_unit: entry.price,
        });
        await new Promise(r => setTimeout(r, 40));
        forcePriceOnLine(getCurrentOrder(screen.pos), entry.price);
    } catch (err) {
        console.error('[CustomBarcode] Error adding product:', err);
        return false;
    }

    const symbol = screen.pos.currency?.symbol ?? '₹';
    showNotification(screen,
        `${entry.product_name}  ×  ${entry.qty}  =  ${symbol}${(entry.qty * entry.price).toFixed(2)}`
    );
    screen.numberBuffer?.reset?.();
    return true;
}

// ── Patch ProductScreen ───────────────────────────────────────────────────────
patch(ProductScreen.prototype, {

    setup() {
        super.setup();

        // Pre-warm barcode cache
        fetchCustomBarcodeMap().catch(() => {});

        // After the component mounts, find the search input and listen for Enter
        onMounted(() => {
            // Try multiple selectors Odoo 19 uses for the search bar input
            const selectors = [
                '.search-bar input',
                '.pos-search-bar input',
                'input.product-search-input',
                '.product-screen .search input',
                'input[placeholder*="earch"]',
                '.search input',
            ];

            let input = null;
            for (const sel of selectors) {
                input = document.querySelector(sel);
                if (input) { console.log(`[CustomBarcode] Search input found: "${sel}"`); break; }
            }

            if (!input) {
                // Fallback: find any visible input in the POS screen
                const all = document.querySelectorAll('input[type="text"], input:not([type])');
                for (const el of all) {
                    if (el.offsetParent !== null) { input = el; break; }
                }
                console.log('[CustomBarcode] Search input (fallback):', input);
            }

            if (input) {
                this._customBarcodeKeyHandler = async (evt) => {
                    if (evt.key !== 'Enter') return;
                    const word = input.value?.trim();
                    if (!word) return;

                    console.log('[CustomBarcode] Search Enter pressed, value:', word);
                    const handled = await handleCustomBarcode(this, word);
                    if (handled) {
                        evt.preventDefault();
                        evt.stopImmediatePropagation();
                        // Clear the search input
                        input.value = '';
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                        // Also clear POS internal search state
                        try { this.updateSearch?.(''); } catch(e) {}
                        try { if (this.state) this.state.searchWord = ''; } catch(e) {}
                    }
                };
                input.addEventListener('keydown', this._customBarcodeKeyHandler, true);
                this._customBarcodeInput = input;
            } else {
                console.warn('[CustomBarcode] ⚠️ Could not find search input element.');
            }
        });

        onWillUnmount(() => {
            if (this._customBarcodeInput && this._customBarcodeKeyHandler) {
                this._customBarcodeInput.removeEventListener(
                    'keydown', this._customBarcodeKeyHandler, true
                );
            }
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

console.log('[CustomBarcode] ✅ v18 loaded — scanner + manual search handled.');
