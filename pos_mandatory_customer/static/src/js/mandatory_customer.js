/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { _t } from "@web/core/l10n/translation";

/**
 * Robust partner check covering ALL formats Odoo 19 POS may use:
 *
 *   false / null / undefined   → no customer
 *   0                          → no customer
 *   7          (integer id)    → customer set
 *   [7, "Ali"] (Many2one arr)  → customer set  ← THIS was the bug
 *   { id: 7, name: "Ali" }    → customer set
 */
function hasCustomer(pos) {
    const order = pos.currentOrder;
    if (!order) return false;

    const p = order.partner_id;

    if (!p) return false;                           // false / null / undefined / 0
    if (Array.isArray(p)) return p[0] > 0;         // [id, name] — Odoo Many2one tuple
    if (typeof p === "object") return !!p.id;       // { id, name } object
    return Number(p) > 0;                           // raw integer id
}

function showWarning(notification) {
    notification.add(
        _t("Please select a customer before processing the payment."),
        { type: "danger", title: _t("Customer Required"), sticky: false }
    );
}

// ── 1. Block on ORDER SCREEN quick-pay buttons ────────────────────────────────
patch(ProductScreen.prototype, {

    async selectPaymentMethod(paymentMethod) {
        if (!hasCustomer(this.pos)) {
            showWarning(this.notification);
            return;
        }
        await super.selectPaymentMethod(...arguments);
    },

    async clickPaymentMethod(paymentMethod) {
        if (!hasCustomer(this.pos)) {
            showWarning(this.notification);
            return;
        }
        await super.clickPaymentMethod(...arguments);
    },

    async pay() {
        if (!hasCustomer(this.pos)) {
            showWarning(this.notification);
            return;
        }
        await super.pay();
    },
});

// ── 2. Last-line defence on PAYMENT SCREEN Validate button ────────────────────
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
