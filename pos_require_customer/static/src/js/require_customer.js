/** @odoo-module **/

import { patch }      from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { Component }  from "@odoo/owl";

import { PaymentScreen }  from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ProductScreen }  from "@point_of_sale/app/screens/product_screen/product_screen";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";

console.log("[pos_require_customer] FINAL HARD STOP VERSION LOADED");

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
function noCustomerOnOrder(order) {
    try {
        if (!order) return false;

        return !(
            order.get_partner?.() ||
            order.getPartner?.() ||
            order.partner ||
            order.partner_id
        );
    } catch (e) {
        console.warn("[pos_require_customer] error:", e);
        return false;
    }
}

async function showPopup(dialogService, body) {
    return new Promise((resolve) => {
        dialogService.add(CustomerRequiredDialog, {
            title: "Customer Required",
            body,
            close: resolve,
        });
    });
}

// ─────────────────────────────────────────────
// 🔥 ActionpadWidget (MAIN FIX HERE)
// ─────────────────────────────────────────────
patch(ActionpadWidget.prototype, {
    setup() {
        super.setup(...arguments);
        this._rcDialog = useService("dialog");
        console.log("[pos_require_customer] ActionpadWidget patched ✓");
    },

    // 🔥 ONE-CLICK PAYMENT FIX (Cash KDTY / Card KDTY)
    async fastValidate(paymentMethod) {
        if (noCustomerOnOrder(this.currentOrder)) {
            await showPopup(this._rcDialog, "Please select a customer before payment.");

            // 🔥 HARD STOP (VERY IMPORTANT)
            throw new Error("BLOCK PAYMENT - NO CUSTOMER");
        }

        return super.fastValidate.apply(this, arguments);
    },

    // Payment button
    async pay() {
        if (noCustomerOnOrder(this.currentOrder)) {
            await showPopup(this._rcDialog, "Please select a customer before payment.");

            // 🔥 HARD STOP
            throw new Error("BLOCK PAYMENT - NO CUSTOMER");
        }

        return super.pay(...arguments);
    },
});

// ─────────────────────────────────────────────
// ProductScreen (extra safety)
// ─────────────────────────────────────────────
patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this._rcDialog = useService("dialog");

        const pos = this.pos;
        const dialog = this._rcDialog;

        if (pos?.pay && !pos.__rc_pay_wrapped__) {
            const original = pos.pay.bind(pos);

            pos.pay = async (...args) => {
                if (noCustomerOnOrder(pos.get_order())) {
                    await showPopup(dialog, "Please select a customer before payment.");
                    throw new Error("BLOCK PAYMENT - NO CUSTOMER");
                }
                return original(...args);
            };

            pos.__rc_pay_wrapped__ = true;
        }
    },
});

// ─────────────────────────────────────────────
// PaymentScreen (final safety)
// ─────────────────────────────────────────────
patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this._rcDialog = useService("dialog");
        console.log("[pos_require_customer] PaymentScreen patched ✓");
    },

    async validateOrder(isForceValidate) {
        if (noCustomerOnOrder(this.pos.get_order())) {
            await showPopup(this._rcDialog, "Please select a customer before completing payment.");
            throw new Error("BLOCK PAYMENT - NO CUSTOMER");
        }
        return super.validateOrder(...arguments);
    },

    async validateOrderFast() {
        if (noCustomerOnOrder(this.pos.get_order())) {
            await showPopup(this._rcDialog, "Please select a customer before completing payment.");
            throw new Error("BLOCK PAYMENT - NO CUSTOMER");
        }
        return super.validateOrderFast?.(...arguments);
    },
});