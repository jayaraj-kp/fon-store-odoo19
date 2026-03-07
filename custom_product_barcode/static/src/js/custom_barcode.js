/** @odoo-module */
/**
 * custom_barcode.js  –  Odoo 19 CE  (v4 — Server-Side Barcode Map)
 * =================================================================
 *
 * WHY THIS APPROACH
 * -----------------
 * All previous versions tried to read barcode2/barcode3 from the POS
 * product records loaded into JS. In Odoo 19 CE the POS data-loader
 * strictly controls which fields are sent and ignores our overrides,
 * so the fields always arrive as `undefined` in JS.
 *
 * SOLUTION
 * --------
 * We call a dedicated server endpoint  POST /pos/custom_barcode_map
 * once when the POS opens. The server queries product.template directly
 * (where barcode2/barcode3 definitely exist) and returns a plain JSON map:
 *
 *   { "USB3MTR": { product_id:42, qty:12, price:5.0, product_name:"..." },
 *     "BULK120": { product_id:42, qty:120, price:5.0, product_name:"..." } }
 *
 * FLOW
 * ----
 *  1. ProductScreen._barcodeProductAction() is patched.
 *  2. On first scan: fetch barcode map from server (cached for session).
 *  3. Map hit  → find product in POS store → add with qty → done.
 *  4. Map miss → standard Odoo handler (super).
 */

import { patch }         from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

// ── Module-level cache (one map for the whole browser session) ────────────────
let _customBarcodeMap = null;
let _fetchPromise     = null;

// ── Fetch map from Odoo controller ───────────────────────────────────────────
async function fetchCustomBarcodeMap() {
    if (_customBarcodeMap !== null) return _customBarcodeMap;
    if (_fetchPromise)              return _fetchPromise;

    _fetchPromise = (async () => {
        try {
            const response = await fetch('/pos/custom_barcode_map', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ jsonrpc: '2.0', method: 'call', params: {} }),
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const json = await response.json();
            const data = json?.result ?? json;
            _customBarcodeMap = data?.barcodes ?? {};

            const keys = Object.keys(_customBarcodeMap);
            console.log(`[CustomBarcode] ✅ Server map loaded — ${keys.length} barcode(s):`, keys);
        } catch (err) {
            console.error('[CustomBarcode] ❌ Failed to load barcode map:', err);
            _customBarcodeMap = {};
        }
        return _customBarcodeMap;
    })();

    return _fetchPromise;
}

// ── Find product.product in POS store by numeric id ──────────────────────────
function findProductById(pos, productId) {
    try {
        const model = pos.models?.['product.product'];
        if (!model) return null;
        if (typeof model.getBy  === 'function') return model.getBy('id', productId) || null;
        if (typeof model.get    === 'function') return model.get(productId) || null;
        if (model.records) {
            return model.records[productId]
                || Object.values(model.records).find(p => p.id === productId)
                || null;
        }
    } catch (e) { console.error('[CustomBarcode] findProductById:', e); }
    return null;
}

// ── Add product + qty to current order (Odoo 17/18/19 fallbacks) ─────────────
async function addProductWithQty(screen, product, qty) {
    const pos = screen.pos;
    if (typeof pos.addProductToCurrentOrder === 'function') {
        await pos.addProductToCurrentOrder(product, { quantity: qty });
        return true;
    }
    if (typeof screen.addProductToOrder === 'function') {
        await screen.addProductToOrder(product);
        const order = pos.get_order?.() || pos.selectedOrder;
        const line  = order?.get_selected_orderline?.() || order?.selected_orderline;
        if (line && typeof line.set_quantity === 'function') line.set_quantity(qty);
        return true;
    }
    const order = pos.get_order?.() || pos.selectedOrder;
    if (order && typeof order.add_product === 'function') {
        order.add_product(product, { quantity: qty });
        return true;
    }
    return false;
}

// ── Patch ProductScreen ───────────────────────────────────────────────────────
patch(ProductScreen.prototype, {

    async _barcodeProductAction(code) {
        const barcodeStr = typeof code === 'string'
            ? code
            : (code?.code ?? code?.base_code ?? code?.value ?? '');

        if (barcodeStr) {
            const map   = await fetchCustomBarcodeMap();
            const entry = map[barcodeStr];

            if (entry) {
                const product = findProductById(this.pos, entry.product_id);

                if (product) {
                    try { await addProductWithQty(this, product, entry.qty); }
                    catch (err) {
                        console.error('[CustomBarcode] add error:', err);
                        return super._barcodeProductAction(code);
                    }
                    try {
                        this.notification?.add(
                            `${entry.product_name}  ×  ${entry.qty}`,
                            { type: 'success', duration: 2500 }
                        );
                    } catch (_) {}
                    this.numberBuffer?.reset?.();
                    return;
                } else {
                    console.warn(
                        `[CustomBarcode] product_id=${entry.product_id} not in POS store. ` +
                        `Ensure the product is enabled for this POS.`
                    );
                }
            }
        }

        return super._barcodeProductAction(code);
    },
});

// Pre-warm cache immediately on module load
fetchCustomBarcodeMap().catch(() => {});

console.log('[CustomBarcode] ✅ v4 loaded — using server-side barcode map.');
