/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    async processBarcode(barcode) {
        const productModel = this.models["product.product"];
        const products = productModel
            ? Object.values(productModel.getAllBy("id") || {})
            : [];

        for (const product of products) {
            let packQty = 0;
            if (product.barcode_2 && product.barcode_2 === barcode) {
                packQty = product.package_qty_2 || 1;
            } else if (product.barcode_3 && product.barcode_3 === barcode) {
                packQty = product.package_qty_3 || 1;
            }
            if (packQty > 0) {
                const order = this.get_order();
                if (order) {
                    order.add_product(product, { quantity: packQty });
                    return true;
                }
            }
        }
        return await super.processBarcode(barcode);
    },
});
