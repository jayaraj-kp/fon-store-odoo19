/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { CustomerPopup } from "@pos_cash_customer_contact/static/src/js/customer_popup";

console.log("✅ POS Payment Patch Loaded");

patch(PaymentScreen.prototype, {

    async validateOrder(isForceValidate) {

        const order = this.pos.getOrder();

        if (!order.getPartner()) {

            console.log("⚠️ No customer → opening popup");

            // Use this.popup (bound via useService in PaymentScreen's setup),
            // NOT this.env.services.popup which is undefined in patched methods.
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