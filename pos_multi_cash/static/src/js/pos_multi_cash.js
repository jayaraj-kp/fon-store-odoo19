/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

/**
 * POS Allow Multiple Cash Payment
 *
 * Patches PosOrder.addPaymentLine to remove the restriction
 * that prevents adding more than one cash-type payment method
 * in a single POS transaction.
 *
 * This allows split payments like: Cash ₹1000 + Card ₹1000
 * even when both payment methods are configured as Cash type.
 */
patch(PosOrder.prototype, {

    addPaymentLine(paymentMethod) {
        // Check if the new payment method is cash type
        const isCashType = paymentMethod.is_cash_count;

        // Check if there's already a cash-type payment line
        const existingCashLine = this.payment_ids.some(
            (pl) => pl.payment_method_id && pl.payment_method_id.is_cash_count
        );

        // If both are cash type, temporarily bypass the cash check
        // by marking the new method as non-cash just for this call,
        // then restoring it immediately after.
        if (isCashType && existingCashLine) {
            paymentMethod.is_cash_count = false;
            const result = super.addPaymentLine(paymentMethod);
            paymentMethod.is_cash_count = isCashType;
            return result;
        }

        // Default behavior for all other cases
        return super.addPaymentLine(paymentMethod);
    },

});
