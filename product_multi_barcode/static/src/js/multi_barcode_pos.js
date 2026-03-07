/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

patch(ProductScreen.prototype, {

    async _getProductByBarcode(code) {
        // First check barcode_2 and barcode_3 on all loaded products
        const barcode = code.base_code;
        const products = Object.values(
            this.pos.models["product.product"].getAllBy("id") || {}
        );

        for (const product of products) {
            if (product.barcode_2 && product.barcode_2 === barcode) {
                product._matchedPackQty = product.package_qty_2 || 1;
                return product;
            }
            if (product.barcode_3 && product.barcode_3 === barcode) {
                product._matchedPackQty = product.package_qty_3 || 1;
                return product;
            }
        }

        // Fall back to default Odoo barcode lookup
        return await super._getProductByBarcode(code);
    },

    async _barcodeProductAction(code) {
        const barcode = code.base_code;
        const products = Object.values(
            this.pos.models["product.product"].getAllBy("id") || {}
        );

        let packQty = null;
        for (const product of products) {
            if (product.barcode_2 && product.barcode_2 === barcode) {
                packQty = product.package_qty_2 || 1;
                break;
            }
            if (product.barcode_3 && product.barcode_3 === barcode) {
                packQty = product.package_qty_3 || 1;
                break;
            }
        }

        if (packQty !== null) {
            // Override qty in code so addLineToCurrentOrder uses it
            const patchedCode = Object.assign({}, code, { quantity: packQty });
            const product = await this._getProductByBarcode(code);
            if (product) {
                await this.pos.addLineToCurrentOrder(
                    { product_id: product, product_tmpl_id: product.product_tmpl_id },
                    { code: patchedCode, quantity: packQty },
                    product.needToConfigure()
                );
                this.numberBuffer.reset();
                this.showOptionalProductPopupIfNeeded(product);
                return;
            }
        }

        // Default handling
        return await super._barcodeProductAction(code);
    },
});
