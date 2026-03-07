/** @odoo-module */
/**
 * custom_barcode.js
 * =================
 * Intercepts POS barcode scanning so that when Barcode 2 or Barcode 3 is
 * scanned the correct package quantity is automatically applied to the order
 * line, producing the right total price.
 *
 * Flow:
 *   1. PosStore is patched to build a fast {barcode → {product, qty}} map
 *      after all products have been loaded from the server.
 *
 *   2. ProductScreen._barcodeProductAction() is patched:
 *        a) Check the custom map first.
 *        b) If found → add product with package qty → done.
 *        c) If not found → fall through to the standard Odoo barcode logic.
 *
 * Tested target: Odoo 19 Community Edition.
 * Compatible with: Odoo 17 / 18 Community Edition (same POS architecture).
 */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

// ─────────────────────────────────────────────────────────────────────────────
// 1.  PosStore  –  build & expose the custom barcode lookup map
// ─────────────────────────────────────────────────────────────────────────────
patch(PosStore.prototype, {

    /**
     * Called after all POS data (products, pricelists, …) has been loaded.
     * We hook here to build our map once the product list is available.
     *
     * Odoo 17/18/19 name: _processData(loadedData)
     * If the method signature ever changes, we still call super first.
     */
    async _processData(loadedData) {
        await super._processData(loadedData);
        this._buildCustomBarcodeMap();
    },

    /**
     * Build a plain-object map:
     *   { "<barcode2_value>": { product: <ProductProduct>, qty: <float> },
     *     "<barcode3_value>": { product: <ProductProduct>, qty: <float> }, … }
     *
     * Called once at startup; also exposed so a UI button could refresh it if
     * products are updated without reloading the POS session.
     */
    _buildCustomBarcodeMap() {
        this._customBarcodeMap = {};

        // In Odoo 17/18/19 the reactive model store exposes all loaded records.
        // product.product inherits template fields via _inherits so barcode2 etc.
        // are directly on the product variant record.
        const products = Object.values(
            this.models?.["product.product"]?.records || {}
        );

        // Fallback: try iterating if .records is not available (API variance)
        const productList = products.length
            ? products
            : (this.models?.["product.product"]?.getAll?.() || []);

        for (const product of productList) {
            if (product.barcode2) {
                this._customBarcodeMap[product.barcode2] = {
                    product,
                    qty: product.custom_qty1 > 0 ? product.custom_qty1 : 1,
                };
            }
            if (product.barcode3) {
                this._customBarcodeMap[product.barcode3] = {
                    product,
                    qty: product.custom_qty2 > 0 ? product.custom_qty2 : 1,
                };
            }
        }

        const count = Object.keys(this._customBarcodeMap).length;
        if (count > 0) {
            console.log(`[CustomBarcode] Indexed ${count} custom package barcode(s).`);
        }
    },

    /**
     * Public helper — look up a barcode in the custom map.
     * Returns { product, qty } or null.
     */
    getProductByCustomBarcode(barcode) {
        if (!this._customBarcodeMap) {
            this._buildCustomBarcodeMap();
        }
        return this._customBarcodeMap[barcode] || null;
    },
});


// ─────────────────────────────────────────────────────────────────────────────
// 2.  ProductScreen  –  intercept _barcodeProductAction
// ─────────────────────────────────────────────────────────────────────────────
patch(ProductScreen.prototype, {

    /**
     * Called whenever a barcode is scanned on the Product Screen.
     *
     * @param {Object|string} code  In Odoo 17/18/19 this is a barcode object
     *                              like { code: "1234567890123", type: "EAN13" }
     *                              but may also be a plain string in some flows.
     */
    async _barcodeProductAction(code) {

        // ── Normalise the barcode value ────────────────────────────────────
        const barcodeStr = typeof code === "string"
            ? code
            : (code?.code ?? code?.base_code ?? code?.value ?? "");

        if (!barcodeStr) {
            return super._barcodeProductAction(code);
        }

        // ── Check custom barcode map ───────────────────────────────────────
        const customData = this.pos.getProductByCustomBarcode(barcodeStr);

        if (customData) {
            const { product, qty } = customData;

            // Retrieve the currently active order
            const order = this.pos.get_order?.()
                       || this.pos.selectedOrder
                       || null;

            if (!order) {
                console.warn("[CustomBarcode] No active order found.");
                return super._barcodeProductAction(code);
            }

            // Add the product with the package quantity.
            // In Odoo 17/18/19: order.add_product(product, options)
            // options.quantity sets the line quantity.
            order.add_product(product, {
                quantity: qty,
            });

            // Optional: show a brief notification so the cashier sees the qty
            try {
                this.notification?.add(
                    `${product.display_name}  ×  ${qty}`,
                    { type: "success", duration: 2000 }
                );
            } catch (_) {
                // notification service not critical — ignore if unavailable
            }

            // Reset the number buffer so the next scan starts fresh
            this.numberBuffer?.reset?.();

            return;   // ← handled; do NOT call super
        }

        // ── Default behaviour (standard barcode, unknown barcode) ──────────
        return super._barcodeProductAction(code);
    },
});
