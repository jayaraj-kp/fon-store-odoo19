/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(PaymentScreen.prototype, {

    async validateOrder(isForceValidate) {
        const currentClient = this.pos.get_client();

        // Get config value (optional but recommended)
        const requireCustomer = this.pos.config.require_customer_for_payment;

        if (requireCustomer && !currentClient) {
            this.env.services.dialog.add(AlertDialog, {
                title: '⚠️ Customer Required',
                body: 'Please select a customer before validating payment.',
            });

            return; // ❌ BLOCK ORDER VALIDATION
        }

        return super.validateOrder(...arguments);
    },

});