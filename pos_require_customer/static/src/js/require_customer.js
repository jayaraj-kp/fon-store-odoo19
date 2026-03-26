/** @odoo-module **/

import { patch }      from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { Component }  from "@odoo/owl";

import { PaymentScreen }  from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ProductScreen }  from "@point_of_sale/app/screens/product_screen/product_screen";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { PosStore } from "@point_of_sale/app/store/pos_store";

console.log("[pos_require_customer] FINAL FIX LOADED");

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
function noCustomer(pos) {
    try {
        const order =
            pos?.get_order?.() ||
            pos?.getOrder?.()  ||
            pos?.selectedOrder ||
            pos?.currentOrder;

        if (!order) return false;

        return !(
            order.get_partner?.() ||
            order.getPartner?.() ||
            order.partner ||
            order.partner_id
        );
    } catch (e) {
        console.warn("noCustomer error:", e);
        return false;
    }
}

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
        console.warn("noCustomerOnOrder error:", e);
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
// 🔥 CRITICAL FIX → BLOCK ALL ONE-CLICK PAYMENTS
// ─────────────────────────────────────────────
patch(PosStore.prototype, {
    async addPaymentLine(paymentMethod) {
        const order = this.get_order();

        if (noCustomerOnOrder(order)) {
            const dialog = this.env.services.dialog;
            await showPopup(dialog, "Please select a customer before payment.");
            return;
        }

        return super.addPaymentLine(...arguments);
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
        if (noCustomerOnOrder(this.currentOrder)) {
            await showPopup(this._rcDialog, "Please select a customer before payment.");
            return;
        }
        return super.fastValidate.apply(this, arguments);
    },

    async pay() {
        if (noCustomerOnOrder(this.currentOrder)) {
            await showPopup(this._rcDialog, "Please select a customer before payment.");
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
        this._rcDialog = useService("dialog");

        const pos = this.pos;
        const dialog = this._rcDialog;

        if (pos?.pay && !pos.__rc_pay_wrapped__) {
            const original = pos.pay.bind(pos);

            pos.pay = async (...args) => {
                if (noCustomer(pos)) {
                    await showPopup(dialog, "Please select a customer before payment.");
                    return;
                }
                return original(...args);
            };

            pos.__rc_pay_wrapped__ = true;
        }
    },
});

// ─────────────────────────────────────────────
// PaymentScreen (Final Safety)
// ─────────────────────────────────────────────
patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this._rcDialog = useService("dialog");
    },

    async validateOrder(isForceValidate) {
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before completing payment.");
            return;
        }
        return super.validateOrder(...arguments);
    },

    async validateOrderFast() {
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before completing payment.");
            return;
        }
        return super.validateOrderFast?.(...arguments);
    },

    async addNewPaymentLine(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before payment.");
            return;
        }
        return super.addNewPaymentLine(...arguments);
    },
});