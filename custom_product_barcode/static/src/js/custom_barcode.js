/** @odoo-module */
/**
 * custom_barcode.js  –  Odoo 19 CE  (v9)
 * ========================================
 * Root fix: Call order.add_product() directly on the Order model.
 * This ALWAYS respects {quantity} regardless of Odoo version.
 * pos.addProductToCurrentOrder() is a store wrapper that strips qty in Odoo 19.
 */

import { patch }         from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

// ── Module-level cache ────────────────────────────────────────────────────────
let _customBarcodeMap = null;
let _fetchPromise     = null;

// ── Fetch barcode map from Odoo controller ────────────────────────────────────
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
            const raw  = (json?.result ?? json)?.barcodes ?? {};

            _customBarcodeMap = {};
            for (const [barcode, entry] of Object.entries(raw)) {
                _customBarcodeMap[barcode.toUpperCase()] = entry;
            }
            console.log(`[CustomBarcode] ✅ Map loaded — ${Object.keys(_customBarcodeMap).length} barcode(s):`, Object.keys(_customBarcodeMap));
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

// ── Safe notification ─────────────────────────────────────────────────────────
function showNotification(screen, message) {
    try {
        const svc = screen.env?.services?.notification;
        if (svc) { svc.add(message, { type: 'success' }); return; }
        if (screen.notification) { screen.notification.add(message, { type: 'success' }); }
    } catch (e) {}
}

// ── Get current order object ──────────────────────────────────────────────────
function getCurrentOrder(pos) {
    return pos.get_order?.()
        || pos.selectedOrder
        || pos.currentOrder
        || null;
}

// ── THE FIX: add product directly on the Order model ─────────────────────────
async function addProductWithQty(screen, product, qty) {
    const pos = screen.pos;

    // ── Method A: Direct order.add_product() — bypasses all store wrappers ────
    // This is the underlying Order model method that has ALWAYS accepted quantity.
    const order = getCurrentOrder(pos);
    if (order && typeof order.add_product === 'function') {
        order.add_product(product, { quantity: qty });
        console.log('[CustomBarcode] ✅ Method A: order.add_product(qty=' + qty + ')');
        return true;
    }

    // ── Method B: store wrapper + force qty on line afterward ─────────────────
    if (typeof pos.addProductToCurrentOrder === 'function') {
        await pos.addProductToCurrentOrder(product, {});
        // Give Owl reactivity a tick to commit the new line
        await new Promise(r => setTimeout(r, 80));

        const freshOrder = getCurrentOrder(pos);
        const line = freshOrder?.get_selected_orderline?.()
                  || freshOrder?.selected_orderline
                  || freshOrder?.selectedOrderline;

        if (line) {
            if (typeof line.set_quantity === 'function') {
                line.set_quantity(String(qty));
                console.log('[CustomBarcode] ✅ Method B: set_quantity(' + qty + ')');
            } else if ('qty' in line) {
                line.qty = qty;
                console.log('[CustomBarcode] ✅ Method B: line.qty=' + qty);
            }
        }
        return true;
    }

    return false;
}

// ── Patch ProductScreen ───────────────────────────────────────────────────────
patch(ProductScreen.prototype, {

    async _barcodeProductAction(code) {
        const raw = typeof code === 'string'
            ? code
            : (code?.code ?? code?.base_code ?? code?.value ?? '');

        const barcodeUpper = raw.toUpperCase();

        if (barcodeUpper) {
            const map   = await fetchCustomBarcodeMap();
            const entry = map[barcodeUpper];

            if (entry) {
                const product = findProductById(this.pos, entry.product_id);

                if (product) {
                    try {
                        await addProductWithQty(this, product, entry.qty);
                    } catch (err) {
                        console.error('[CustomBarcode] add error:', err);
                        return super._barcodeProductAction(code);
                    }
                    showNotification(this, `${entry.product_name}  ×  ${entry.qty}`);
                    this.numberBuffer?.reset?.();
                    return;
                } else {
                    console.warn(`[CustomBarcode] product_id=${entry.product_id} not in POS — enable it in POS config.`);
                }
            }
        }

        return super._barcodeProductAction(code);
    },
});

fetchCustomBarcodeMap().catch(() => {});
console.log('[CustomBarcode] ✅ v9 loaded.');
