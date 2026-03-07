/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

patch(ProductScreen.prototype, {

    async _barcodeProductAction(code) {
        const barcode = code.base_code;

        // Search barcode_2 / barcode_3 across all loaded products
        const productMap = this.pos.models["product.product"].getAllBy("id") || {};
        const products = Object.values(productMap);

        for (const product of products) {
            let packQty = 0;
            if (product.barcode_2 && product.barcode_2 === barcode) {
                packQty = product.package_qty_2 || 1;
            } else if (product.barcode_3 && product.barcode_3 === barcode) {
                packQty = product.package_qty_3 || 1;
            }

            if (packQty > 0) {
                await this.pos.addLineToCurrentOrder(
                    {
                        product_id: product,
                        product_tmpl_id: product.product_tmpl_id,
                        qty: packQty,
                    },
                    { quantity: packQty }
                );
                this.numberBuffer.reset();
                return;
            }
        }

        // Not a pack barcode — use default Odoo handling
        return await super._barcodeProductAction(code);
    },
});
