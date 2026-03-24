/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { _t } from "@web/core/l10n/translation";

patch(PaymentScreen.prototype, {

    /**
     * Override validateOrder to enforce mandatory customer selection.
     * Blocks payment if no customer (partner) is set on the current order.
     */
    async validateOrder(isForceValidate) {
        const order = this.pos.get_order();

        if (!order.get_partner()) {
            // Show danger notification — always available in POS env
            this.notification.add(
                _t("Please select a customer before processing the payment."),
                {
                    type: "danger",
                    title: _t("Customer Required"),
                    sticky: false,
                }
            );
            return; // Block validation
        }

        // Customer is set — proceed with normal flow
        await super.validateOrder(isForceValidate);
    },

    /**
     * Also block quick payment buttons (Cash KDTY / Card KDTY)
     * by intercepting the same validation path.
     */
    async _finalizeValidation() {
        const order = this.pos.get_order();

        if (!order.get_partner()) {
            this.notification.add(
                _t("Please select a customer before processing the payment."),
                {
                    type: "danger",
                    title: _t("Customer Required"),
                    sticky: false,
                }
            );
            return;
        }

        await super._finalizeValidation();
    },
});
