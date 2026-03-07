/** @odoo-module */
/**
 * custom_barcode.js  –  Odoo 19 CE  (v5 — case-insensitive barcode match)
 * ========================================================================
 *
 * FIX in v5: barcode comparison is now CASE-INSENSITIVE.
 * Map keys are stored in UPPERCASE; scanned barcodes are uppercased before
 * lookup.  This means "usb3mtr", "USB3MTR", "Usb3Mtr" all match the same
 * entry.
 */

import { patch }         from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

// ── Module-level cache ────────────────────────────────────────────────────────
let _customBarcodeMap = null;   // keys are UPPERCASE
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

            // ── Store all keys in UPPERCASE for case-insensitive matching ──
            _customBarcodeMap = {};
            for (const [barcode, entry] of Object.entries(raw)) {
                _customBarcodeMap[barcode.toUpperCase()] = entry;
            }

            const keys = Object.keys(_customBarcodeMap);
            console.log(`[CustomBarcode] ✅ Map loaded — ${keys.length} barcode(s):`, keys);
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

// ── Add product + qty (Odoo 17/18/19 fallbacks) ───────────────────────────────
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

        // Normalise to plain string then UPPERCASE for case-insensitive match
        const raw = typeof code === 'string'
            ? code
            : (code?.code ?? code?.base_code ?? code?.value ?? '');

        const barcodeUpper = raw.toUpperCase();

        if (barcodeUpper) {
            const map   = await fetchCustomBarcodeMap();
            const entry = map[barcodeUpper];   // ← keys are already uppercase

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
                    return;   // handled — do NOT call super
                } else {
                    console.warn(
                        `[CustomBarcode] Barcode "${barcodeUpper}" matched map ` +
                        `(product_id=${entry.product_id}) but product not found in POS. ` +
                        `Check: is the product enabled for this POS config?`
                    );
                }
            }
        }

        return super._barcodeProductAction(code);
    },
});

// Pre-warm cache on module load
fetchCustomBarcodeMap().catch(() => {});

console.log('[CustomBarcode] ✅ v5 loaded — case-insensitive server-side barcode map.');
