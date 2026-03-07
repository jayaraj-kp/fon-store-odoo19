/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {

    async processBarcode(barcode) {
        // Try to find product by barcode_2 or barcode_3 first
        const allProducts = Object.values(this.models["product.product"].getAllBy("id") || {});

        let foundProduct = null;
        let packQty = 1;

        for (const product of allProducts) {
            if (product.barcode_2 && product.barcode_2 === barcode) {
                foundProduct = product;
                packQty = product.package_qty_2 || 1;
                break;
            }
            if (product.barcode_3 && product.barcode_3 === barcode) {
                foundProduct = product;
                packQty = product.package_qty_3 || 1;
                break;
            }
        }

        if (foundProduct) {
            const order = this.get_order();
            if (order) {
                order.add_product(foundProduct, { quantity: packQty });
                return true;
            }
        }

        // Fall through to default POS barcode handling
        return await super.processBarcode(barcode);
    },
});
