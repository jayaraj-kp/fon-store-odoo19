/** @odoo-module */
/**
 * custom_barcode.js  –  Odoo 19 CE Multi-Barcode POS Integration
 * ===============================================================
 *
 * FIX vs v1:
 *   - Removed PosStore import (@point_of_sale/app/store/pos_store does NOT
 *     exist in Odoo 19; it was renamed/removed).
 *   - Custom barcode map is now built lazily on first scan, reading directly
 *     from this.pos.models — no separate PosStore patch needed.
 *   - Multi-version fallbacks for the add-to-order API (Odoo 17/18/19).
 *
 * How it works
 * ────────────
 *  1. Patch only ProductScreen._barcodeProductAction(code).
 *  2. On every scan: extract barcode string → check custom map.
 *  3. Map hit  → add product with package qty, show toast, return.
 *  4. Map miss → fall through to standard Odoo handler (super).
 */

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

// ─────────────────────────────────────────────────────────────────────────────
//  Helper – get all loaded product.product records from the POS model store
// ─────────────────────────────────────────────────────────────────────────────
function getAllPosProducts(pos) {
    try {
        const model = pos.models?.["product.product"];
        if (!model) return [];

        // Odoo 18/19 API
        if (typeof model.getAll === "function") return model.getAll();

        // Odoo 17 fallback
        if (model.records && typeof model.records === "object") {
            return Object.values(model.records);
        }
        return [];
    } catch (e) {
        console.error("[CustomBarcode] getAllPosProducts error:", e);
        return [];
    }
}

// ─────────────────────────────────────────────────────────────────────────────
//  Helper – add a product + qty to the current order (multi-version fallback)
// ─────────────────────────────────────────────────────────────────────────────
async function addProductWithQty(screen, product, qty) {
    const pos = screen.pos;

    // Odoo 19
    if (typeof pos.addProductToCurrentOrder === "function") {
        await pos.addProductToCurrentOrder(product, { quantity: qty });
        return;
    }

    // Odoo 17/18: add then set qty on selected line
    if (typeof screen.addProductToOrder === "function") {
        await screen.addProductToOrder(product);
        const order = pos.get_order?.() || pos.selectedOrder;
        if (order) {
            const line = order.get_selected_orderline?.() || order.selected_orderline;
            if (line && typeof line.set_quantity === "function") {
                line.set_quantity(qty);
            }
        }
        return;
    }

    // Odoo 15/16 legacy
    const order = pos.get_order?.() || pos.selectedOrder;
    if (order && typeof order.add_product === "function") {
        order.add_product(product, { quantity: qty });
        return;
    }

    console.error("[CustomBarcode] No compatible add-product API found.");
}

// ─────────────────────────────────────────────────────────────────────────────
//  Patch ProductScreen
// ─────────────────────────────────────────────────────────────────────────────
patch(ProductScreen.prototype, {

    /**
     * Build (and cache) the {barcode → {product, qty}} lookup map.
     * Called lazily on the first scan so products are guaranteed to be loaded.
     */
    _getCustomBarcodeMap() {
        if (this.__customBarcodeMap) return this.__customBarcodeMap;

        const map = {};
        for (const product of getAllPosProducts(this.pos)) {
            if (product.barcode2) {
                map[product.barcode2] = {
                    product,
                    qty: product.custom_qty1 > 0 ? product.custom_qty1 : 1,
                };
            }
            if (product.barcode3) {
                map[product.barcode3] = {
                    product,
                    qty: product.custom_qty2 > 0 ? product.custom_qty2 : 1,
                };
            }
        }

        console.log(
            `[CustomBarcode] Map built — ${Object.keys(map).length} custom barcode(s) indexed.`
        );
        this.__customBarcodeMap = map;
        return map;
    },

    /**
     * Intercept every POS barcode scan.
     * code may be a plain string or a barcode object {code, type, …}.
     */
    async _barcodeProductAction(code) {
        // Normalise to string
        const barcodeStr =
            typeof code === "string"
                ? code
                : (code?.code ?? code?.base_code ?? code?.value ?? "");

        if (barcodeStr) {
            const customData = this._getCustomBarcodeMap()[barcodeStr];

            if (customData) {
                const { product, qty } = customData;

                try {
                    await addProductWithQty(this, product, qty);
                } catch (err) {
                    console.error("[CustomBarcode] Error adding product:", err);
                    return super._barcodeProductAction(code);
                }

                // Toast — non-critical
                try {
                    this.notification?.add(
                        `${product.display_name}  ×  ${qty}`,
                        { type: "success", duration: 2000 }
                    );
                } catch (_) {}

                this.numberBuffer?.reset?.();
                return;   // handled — do NOT call super
            }
        }

        // Not a custom barcode → fall through to standard Odoo handler
        return super._barcodeProductAction(code);
    },
});

console.log("[CustomBarcode] ✅ ProductScreen._barcodeProductAction patched.");
