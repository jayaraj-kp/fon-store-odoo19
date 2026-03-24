/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { _t } from "@web/core/l10n/translation";

// Helper: check if current order has a customer set
function hasCustomer(pos) {
    const order = pos.currentOrder;
    return order && order.partner_id;
}

// ── 1. Block quick Cash/Card buttons on the ORDER SCREEN ──────────────────────
patch(ProductScreen.prototype, {

    // Called when user clicks Cash CHLR / Card CHLR directly on order screen
    async clickPaymentMethod(paymentMethod) {
        if (!hasCustomer(this.pos)) {
            this.notification.add(
                _t("Please select a customer before processing the payment."),
                { type: "danger", title: _t("Customer Required"), sticky: false }
            );
            return; // Never enters payment screen
        }
        await super.clickPaymentMethod(paymentMethod);
    },

    // Fallback: also guard the Payment button
    async pay() {
        if (!hasCustomer(this.pos)) {
            this.notification.add(
                _t("Please select a customer before processing the payment."),
                { type: "danger", title: _t("Customer Required"), sticky: false }
            );
            return;
        }
        await super.pay();
    },
});

// ── 2. Last-line defence on PAYMENT SCREEN Validate button ────────────────────
patch(PaymentScreen.prototype, {

    async validateOrder(isForceValidate) {
        if (!hasCustomer(this.pos)) {
            this.notification.add(
                _t("Please select a customer before processing the payment."),
                { type: "danger", title: _t("Customer Required"), sticky: false }
            );
            return;
        }
        await super.validateOrder(isForceValidate);
    },

    async _finalizeValidation() {
        if (!hasCustomer(this.pos)) {
            this.notification.add(
                _t("Please select a customer before processing the payment."),
                { type: "danger", title: _t("Customer Required"), sticky: false }
            );
            return;
        }
        await super._finalizeValidation();
    },
});
