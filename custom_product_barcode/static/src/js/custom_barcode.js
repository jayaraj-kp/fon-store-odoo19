/** @odoo-module */
/**
 * custom_barcode.js  –  Odoo 19 CE  (v6)
 * ========================================
 * Fixes: Notification component crash — Odoo 19 uses this.env.services.notification
 * instead of this.notification, and does NOT accept a 'duration' prop.
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

            // Store keys as UPPERCASE for case-insensitive matching
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

// ── Show a safe notification (handles Odoo 17/18/19 API differences) ─────────
function showNotification(screen, message) {
    try {
        // Odoo 19: notification service via env
        const svc = screen.env?.services?.notification;
        if (svc) {
            svc.add(message, { type: 'success' });
            return;
        }
        // Odoo 17/18: this.notification
        if (screen.notification) {
            screen.notification.add(message, { type: 'success' });
            return;
        }
    } catch (e) {
        // Notification is cosmetic — never crash on it
        console.warn('[CustomBarcode] Notification skipped:', e.message);
    }
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

                    // Safe notification — will never crash POS even if API changes
                    showNotification(this, `${entry.product_name}  ×  ${entry.qty}`);

                    this.numberBuffer?.reset?.();
                    return;   // handled — do NOT call super
                } else {
                    console.warn(
                        `[CustomBarcode] Barcode "${barcodeUpper}" matched ` +
                        `(product_id=${entry.product_id}) but product not in POS. ` +
                        `Enable it for this POS configuration.`
                    );
                }
            }
        }

        return super._barcodeProductAction(code);
    },
});

// Pre-warm cache on module load
fetchCustomBarcodeMap().catch(() => {});

console.log('[CustomBarcode] ✅ v6 loaded.');
