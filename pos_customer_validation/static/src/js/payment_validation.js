/** @odoo-module */

console.log("✅ POS Customer Validation JS LOADED");

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {

        console.log("🔥 validateOrder triggered");

        const currentClient = this.pos.get_client();
        const requireCustomer = this.pos.config.require_customer_for_payment;

        if (requireCustomer && !currentClient) {
            this.env.services.dialog.add(AlertDialog, {
                title: 'Customer Required',
                body: 'Please select a customer before payment.',
            });
            return;
        }

        return super.validateOrder(...arguments);
    },
});