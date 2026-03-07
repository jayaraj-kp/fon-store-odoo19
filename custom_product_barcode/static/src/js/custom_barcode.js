/** @odoo-module */
/**
 * custom_barcode.js  –  Odoo 19 CE  (v7)
 * ========================================
 * Fix: addProductToCurrentOrder in Odoo 19 ignores {quantity} option.
 * After adding, we explicitly set qty on the selected order line.
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

// ── Get the currently selected order line ────────────────────────────────────
function getSelectedLine(pos) {
    const order = pos.get_order?.() || pos.selectedOrder || pos.currentOrder;
    if (!order) return null;
    return order.get_selected_orderline?.()
        || order.selected_orderline
        || order.selectedOrderline
        || null;
}

// ── Show safe notification ────────────────────────────────────────────────────
function showNotification(screen, message) {
    try {
        const svc = screen.env?.services?.notification;
        if (svc) { svc.add(message, { type: 'success' }); return; }
        if (screen.notification) { screen.notification.add(message, { type: 'success' }); }
    } catch (e) {
        console.warn('[CustomBarcode] Notification skipped:', e.message);
    }
}

// ── Add product then FORCE the quantity on the resulting line ─────────────────
async function addProductWithQty(screen, product, qty) {
    const pos = screen.pos;

    // ── Odoo 19: addProductToCurrentOrder exists but ignores quantity option ──
    if (typeof pos.addProductToCurrentOrder === 'function') {
        await pos.addProductToCurrentOrder(product, { quantity: qty });

        // Odoo 19 ignores {quantity} — set it explicitly on the selected line
        const line = getSelectedLine(pos);
        if (line) {
            // Try reactive assignment first (Odoo 19 uses reactive state)
            if (typeof line.set_quantity === 'function') {
                line.set_quantity(String(qty));   // some builds expect string
            } else if ('qty' in line) {
                line.qty = qty;
            } else if ('quantity' in line) {
                line.quantity = qty;
            }
            console.log(`[CustomBarcode] Line qty set to ${qty} on`, line);
        } else {
            console.warn('[CustomBarcode] Could not find selected line to set qty.');
        }
        return true;
    }

    // ── Odoo 17/18 ────────────────────────────────────────────────────────────
    if (typeof screen.addProductToOrder === 'function') {
        await screen.addProductToOrder(product);
        const line = getSelectedLine(pos);
        if (line && typeof line.set_quantity === 'function') {
            line.set_quantity(String(qty));
        }
        return true;
    }

    // ── Legacy fallback ───────────────────────────────────────────────────────
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

                    showNotification(this, `${entry.product_name}  ×  ${entry.qty}`);
                    this.numberBuffer?.reset?.();
                    return;
                } else {
                    console.warn(
                        `[CustomBarcode] product_id=${entry.product_id} not in POS. ` +
                        `Enable it in this POS configuration.`
                    );
                }
            }
        }

        return super._barcodeProductAction(code);
    },
});

// Pre-warm cache on module load
fetchCustomBarcodeMap().catch(() => {});
console.log('[CustomBarcode] ✅ v7 loaded.');
