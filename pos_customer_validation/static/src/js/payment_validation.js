/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(PaymentScreen.prototype, {
    /**
     * Override addPaymentLine to validate customer selection
     * Prevents payment processing without a customer
     */
    async addPaymentLine(paymentMethod) {
        // Get the currently selected customer
        const currentClient = this.pos.get_client();
        
        // Check if customer is selected
        if (!currentClient) {
            // Show popup warning
            this.env.services.dialog.add(AlertDialog, {
                title: '⚠️ Customer Required',
                body: 'Please select a customer before proceeding with payment.',
            });
            
            // Block payment processing
            return;
        }
        
        // Customer is selected, proceed with payment
        return super.addPaymentLine(...arguments);
    },
});
