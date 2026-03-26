/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";

console.log("[pos_require_customer] RUNTIME PATCH VERSION LOADED");

// ─────────────────────────────────────────────
// Dialog
// ─────────────────────────────────────────────
export class CustomerRequiredDialog extends Component {
    static template = "pos_require_customer.CustomerRequiredDialog";
    static props = { close: Function };

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
// 🔥 RUNTIME PATCH (NO IMPORT)
// ─────────────────────────────────────────────
setTimeout(() => {
    try {
        const pos = odoo.__WOWL_DEBUG__?.root?.env?.services?.pos;
        const order = pos?.get_order?.();

        if (!order) {
            console.warn("Order not found for patch");
            return;
        }

        const proto = Object.getPrototypeOf(order);

        if (proto.__rc_patched__) return;

        const original = proto.add_paymentline;

        proto.add_paymentline = function (...args) {
            if (!hasCustomer(this)) {
                this.env.services.dialog.add(CustomerRequiredDialog, {
                    title: "Customer Required",
                    body: "Please select a customer before payment.",
                });
                return;
            }
            return original.apply(this, args);
        };

        proto.__rc_patched__ = true;

        console.log("[pos_require_customer] Order patched dynamically ✅");

    } catch (e) {
        console.error("Runtime patch failed:", e);
    }
}, 2000);

// ─────────────────────────────────────────────
// ActionpadWidget (normal flow)
// ─────────────────────────────────────────────
patch(ActionpadWidget.prototype, {
    setup() {
        super.setup(...arguments);
        this._rcDialog = useService("dialog");
    },

    async fastValidate() {
        if (!hasCustomer(this.currentOrder)) {
            await this._rcDialog.add(CustomerRequiredDialog, {
                title: "Customer Required",
                body: "Please select a customer before payment.",
            });
            return;
        }
        return super.fastValidate.apply(this, arguments);
    },

    async pay() {
        if (!hasCustomer(this.currentOrder)) {
            await this._rcDialog.add(CustomerRequiredDialog, {
                title: "Customer Required",
                body: "Please select a customer before payment.",
            });
            return;
        }
        return super.pay(...arguments);
    },
});

// ─────────────────────────────────────────────
// PaymentScreen safety
// ─────────────────────────────────────────────
patch(PaymentScreen.prototype, {
    async validateOrder() {
        if (!hasCustomer(this.pos.get_order())) {
            this.env.services.dialog.add(CustomerRequiredDialog, {
                title: "Customer Required",
                body: "Please select a customer before completing payment.",
            });
            return;
        }
        return super.validateOrder(...arguments);
    },
});