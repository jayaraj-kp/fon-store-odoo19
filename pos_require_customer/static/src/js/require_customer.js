/** @odoo-module **/

import { patch }      from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { Component }  from "@odoo/owl";

import { PaymentScreen }  from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ProductScreen }  from "@point_of_sale/app/screens/product_screen/product_screen";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";

// ⚠️ Try this path first
import { Order } from "@point_of_sale/app/models/order";

console.log("[pos_require_customer] FINAL HARD BLOCK VERSION LOADED");

// ─────────────────────────────────────────────
// Dialog Component
// ─────────────────────────────────────────────
export class CustomerRequiredDialog extends Component {
    static template = "pos_require_customer.CustomerRequiredDialog";
    static props = {
        title: { type: String, optional: true },
        body:  { type: String, optional: true },
        close: { type: Function, optional: true },
    };
    confirm() {
        this.props.close?.();
    }
}

// ─────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────
function hasCustomer(order) {
    return !!(
        order?.get_partner?.() ||
        order?.getPartner?.() ||
        order?.partner ||
        order?.partner_id
    );
}

async function showPopup(env, body) {
    return new Promise((resolve) => {
        env.services.dialog.add(CustomerRequiredDialog, {
            title: "Customer Required",
            body,
            close: resolve,
        });
    });
}

// ─────────────────────────────────────────────
// 🔥 MODEL LEVEL (MOST IMPORTANT)
// Blocks ALL payment additions (including KDTY)
// ─────────────────────────────────────────────
patch(Order.prototype, {
    add_paymentline(payment_method) {
        if (!hasCustomer(this)) {
            const env = this.env;

            env.services.dialog.add(CustomerRequiredDialog, {
                title: "Customer Required",
                body: "Please select a customer before payment.",
            });

            return; // 🚫 BLOCK EVERYTHING HERE
        }

        return super.add_paymentline(...arguments);
    },
});

// ─────────────────────────────────────────────
// ActionpadWidget
// ─────────────────────────────────────────────
patch(ActionpadWidget.prototype, {
    setup() {
        super.setup(...arguments);
        this._rcDialog = useService("dialog");
    },

    async fastValidate(paymentMethod) {
        if (!hasCustomer(this.currentOrder)) {
            await showPopup(this.env, "Please select a customer before payment.");
            return;
        }
        return super.fastValidate.apply(this, arguments);
    },

    async pay() {
        if (!hasCustomer(this.currentOrder)) {
            await showPopup(this.env, "Please select a customer before payment.");
            return;
        }
        return super.pay(...arguments);
    },
});

// ─────────────────────────────────────────────
// ProductScreen
// ─────────────────────────────────────────────
patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);

        const pos = this.pos;

        if (pos?.pay && !pos.__rc_pay_wrapped__) {
            const original = pos.pay.bind(pos);

            pos.pay = async (...args) => {
                if (!hasCustomer(pos.get_order())) {
                    await showPopup(this.env, "Please select a customer before payment.");
                    return;
                }
                return original(...args);
            };

            pos.__rc_pay_wrapped__ = true;
        }
    },
});

// ─────────────────────────────────────────────
// PaymentScreen (safety)
// ─────────────────────────────────────────────
patch(PaymentScreen.prototype, {
    async addNewPaymentLine(paymentMethod) {
        if (!hasCustomer(this.pos.get_order())) {
            await showPopup(this.env, "Please select a customer before payment.");
            return;
        }
        return super.addNewPaymentLine(...arguments);
    },

    async validateOrder(isForceValidate) {
        if (!hasCustomer(this.pos.get_order())) {
            await showPopup(this.env, "Please select a customer before completing payment.");
            return;
        }
        return super.validateOrder(...arguments);
    },

    async validateOrderFast() {
        if (!hasCustomer(this.pos.get_order())) {
            await showPopup(this.env, "Please select a customer before completing payment.");
            return;
        }
        return super.validateOrderFast?.(...arguments);
    },
});