/** @odoo-module **/

/**
 * product_multi_barcode – POS barcode patch
 *
 * Overrides the default POS barcode scanning so that when barcode_2 or
 * barcode_3 is scanned the correct product + package quantity is used.
 */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {

    /**
     * Find a product by scanning any of the 3 barcode slots.
     * Returns { product, qty, label } or null.
     */
    _getProductByAnyBarcode(barcode) {
        const allProducts = this.db.get_product_by_barcode(barcode);
        if (allProducts) {
            // standard slot found – qty = 1
            return { product: allProducts, qty: 1, label: allProducts.display_name };
        }

        // Check barcode_2 and barcode_3 on every loaded product
        for (const product of Object.values(this.db.product_by_id)) {
            if (product.barcode_2 && product.barcode_2 === barcode) {
                const qty   = product.package_qty_2 || 1;
                const label = product.package_name_2 || (product.display_name + " (Pack 2)");
                return { product, qty, label };
            }
            if (product.barcode_3 && product.barcode_3 === barcode) {
                const qty   = product.package_qty_3 || 1;
                const label = product.package_name_3 || (product.display_name + " (Pack 3)");
                return { product, qty, label };
            }
        }
        return null;
    },

    /**
     * Patch the main barcode action so our multi-barcode lookup fires first.
     */
    async scan_product(code) {
        const barcode = code.code || code;
        const found   = this._getProductByAnyBarcode(barcode);

        if (!found) {
            // fall through to the default handler (customer card, etc.)
            return super.scan_product(code);
        }

        const { product, qty, label } = found;
        const order = this.get_order();

        if (!order) return false;

        // Add the product with the calculated package qty
        order.add_product(product, { quantity: qty, description: label });
        return true;
    },
});
