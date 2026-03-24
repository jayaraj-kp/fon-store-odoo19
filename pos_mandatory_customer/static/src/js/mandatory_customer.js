/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { _t } from "@web/core/l10n/translation";

/**
 * Robust partner check for Odoo 19 POS.
 * partner_id can be:
 *   - false / null / undefined  → no customer
 *   - a number (id)             → customer set
 *   - an object { id, name }    → customer set
 */
function hasCustomer(pos) {
    const order = pos.currentOrder;
    if (!order) return false;
    const p = order.partner_id;
    if (!p) return false;
    if (typeof p === "object") return !!p.id;  // { id: X, name: "..." }
    return p > 0;                               // raw numeric id
}

function showWarning(notification) {
    notification.add(
        _t("Please select a customer before processing the payment."),
        { type: "danger", title: _t("Customer Required"), sticky: false }
    );
}

// ── 1. Block on ORDER SCREEN quick-pay buttons ─────────────────────────────────
patch(ProductScreen.prototype, {

    // Odoo 19: quick pay buttons call this method
    async selectPaymentMethod(paymentMethod) {
        if (!hasCustomer(this.pos)) {
            showWarning(this.notification);
            return;
        }
        await super.selectPaymentMethod(...arguments);
    },

    // Some builds still use this name — patch both to be safe
    async clickPaymentMethod(paymentMethod) {
        if (!hasCustomer(this.pos)) {
            showWarning(this.notification);
            return;
        }
        await super.clickPaymentMethod(...arguments);
    },

    // Guard the main Payment button too
    async pay() {
        if (!hasCustomer(this.pos)) {
            showWarning(this.notification);
            return;
        }
        await super.pay();
    },
});

// ── 2. Last-line defence on PAYMENT SCREEN Validate ───────────────────────────
patch(PaymentScreen.prototype, {

    async validateOrder(isForceValidate) {
        if (!hasCustomer(this.pos)) {
            showWarning(this.notification);
            return;
        }
        await super.validateOrder(isForceValidate);
    },

    async _finalizeValidation() {
        if (!hasCustomer(this.pos)) {
            showWarning(this.notification);
            return;
        }
        await super._finalizeValidation();
    },
});
