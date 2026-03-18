/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

/**
 * POS Allow Multiple Cash Payment
 *
 * Patches PaymentScreen.addNewPaymentLine to remove the restriction
 * that prevents adding more than one cash-type payment method
 * in a single POS transaction.
 *
 * This allows split payments like: Cash ₹1000 + Card ₹1000
 * even when both payment methods are configured as Cash type.
 */
patch(PaymentScreen.prototype, {

    async addNewPaymentLine(paymentMethod) {
        // Temporarily mark the payment method as non-cash
        // to bypass the "already a cash payment line" check
        const originalIsCash = paymentMethod.is_cash_count;
        const currentOrder = this.currentOrder;

        const hasCashLine = currentOrder.payment_ids.some(
            (pl) => pl.payment_method_id && pl.payment_method_id.is_cash_count
        );

        if (originalIsCash && hasCashLine) {
            paymentMethod.is_cash_count = false;
            const result = await super.addNewPaymentLine(paymentMethod);
            paymentMethod.is_cash_count = originalIsCash;
            return result;
        }

        return await super.addNewPaymentLine(paymentMethod);
    },

});
