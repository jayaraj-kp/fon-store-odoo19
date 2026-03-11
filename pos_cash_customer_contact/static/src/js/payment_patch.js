/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { CustomerPopup } from "@pos_cash_customer_contact/js/customer_popup";

console.log("✅ POS Payment Patch Loaded");

patch(PaymentScreen.prototype, {

    async validateOrder(isForceValidate) {

        const order = this.pos.getOrder();

        if (!order.get_partner()) {

            console.log("⚠️ No customer → opening popup");

            const { confirmed } = await this.popup.add(CustomerPopup, {
                title: "Customer Required",
            });

            if (!confirmed) {
                return;
            }
        }

        return super.validateOrder(...arguments);
    }

});