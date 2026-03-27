/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

patch(ProductScreen.prototype, {

    async _onClickPayButton(event) {
        // This patches the main "Payment" button
        const order = this.pos.get_order();
        if (!order.get_partner()) {
            this.popup.add(ErrorPopup, {
                title: "Customer Required",
                body: "Please select a customer before proceeding with payment.",
            });
            return;
        }
        return super._onClickPayButton(...arguments);
    },

});