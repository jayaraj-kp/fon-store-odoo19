/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(PaymentScreen.prototype, {
    async addPaymentLine(paymentMethod) {
        const currentClient = this.pos.get_client();
        
        // Check if customer is selected before processing payment
        if (!currentClient) {
            // Show warning dialog
            this.env.services.dialog.add(AlertDialog, {
                title: 'Missing Customer',
                body: 'Please select a customer before proceeding with payment (Cash KDTY or Card KDTY).',
            });
            return;
        }
        
        // If customer is selected, proceed with original method
        return super.addPaymentLine(...arguments);
    },
});
