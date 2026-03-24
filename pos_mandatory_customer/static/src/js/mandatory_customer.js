/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { _t } from "@web/core/l10n/translation";

/**
 * Odoo 19 POS facts (confirmed via console debug):
 *  - Active order lives at pos.selectedOrder  (NOT pos.currentOrder)
 *  - partner_id is a Proxy(ResPartner) ORM record when set
 *  - When no customer: partner_id is false/null/undefined
 *  - When customer set: partner_id.id is a positive integer
 */
function hasCustomer(pos) {
    // Use selectedOrder — currentOrder is undefined in this build
    const order = pos.selectedOrder || pos.currentOrder;
    if (!order) return false;

    const p = order.partner_id;

    // No partner at all
    if (!p) return false;

    // Odoo 19 ORM Proxy(ResPartner) — access .id directly on the proxy
    if (typeof p === "object") {
        // Try .id first (ORM record proxy)
        if (p.id !== undefined && p.id !== null && p.id !== false) {
            return Number(p.id) > 0;
        }
        // Fallback: Many2one array [id, name]
        if (Array.isArray(p)) return Number(p[0]) > 0;
        return false;
    }

    // Raw integer id
    return Number(p) > 0;
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
