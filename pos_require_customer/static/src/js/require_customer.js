/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";

console.log("[pos_require_customer] FINAL OVERRIDE VERSION LOADED");

// ─────────────────────────────────────────────
// Dialog Component
// ─────────────────────────────────────────────
export class CustomerRequiredDialog extends Component {
    static template = "pos_require_customer.CustomerRequiredDialog";
    static props = {
        title: { type: String, optional: true },
        body: { type: String, optional: true },
        close: { type: Function, optional: true },
    };
    confirm() {
        this.props.close?.();
    }
}

// ─────────────────────────────────────────────
// Helper
// ─────────────────────────────────────────────
function hasCustomer(order) {
    return !!(
        order?.get_partner?.() ||
        order?.getPartner?.() ||
        order?.partner ||
        order?.partner_id
    );
}

// ─────────────────────────────────────────────
// 🔥 MASTER OVERRIDE (MOST IMPORTANT)
// This replaces ORIGINAL fastValidate completely
// ─────────────────────────────────────────────
const originalFastValidate = ActionpadWidget.prototype.fastValidate;

ActionpadWidget.prototype.fastValidate = async function (paymentMethod) {

    const order = this.currentOrder;

    if (!hasCustomer(order)) {
        this.env.services.dialog.add(CustomerRequiredDialog, {
            title: "Customer Required",
            body: "Please select a customer before payment.",
        });

        // 🚫 HARD BLOCK → DO NOT CONTINUE
        return;
    }

    // ✅ Continue only if customer exists
    return await originalFastValidate.apply(this, arguments);
};

// ─────────────────────────────────────────────
// ALSO BLOCK PAY BUTTON
// ─────────────────────────────────────────────
const originalPay = ActionpadWidget.prototype.pay;

ActionpadWidget.prototype.pay = async function () {

    const order = this.currentOrder;

    if (!hasCustomer(order)) {
        this.env.services.dialog.add(CustomerRequiredDialog, {
            title: "Customer Required",
            body: "Please select a customer before payment.",
        });

        return;
    }

    return await originalPay.apply(this, arguments);
};

// ─────────────────────────────────────────────
// PaymentScreen (final safety)
// ─────────────────────────────────────────────
patch(PaymentScreen.prototype, {
    async validateOrder() {
        const order = this.pos.get_order();

        if (!hasCustomer(order)) {
            this.env.services.dialog.add(CustomerRequiredDialog, {
                title: "Customer Required",
                body: "Please select a customer before completing payment.",
            });
            return;
        }

        return super.validateOrder(...arguments);
    },
});