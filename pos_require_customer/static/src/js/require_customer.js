/** @odoo-module */

console.log("[pos_require_customer] v12 - clean fix loaded");

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

class CustomerRequiredDialog extends Component {
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

function noCustomer(pos) {
    try {
        const order = pos?.get_order?.()
            || pos?.getOrder?.()
            || pos?.selectedOrder
            || pos?.currentOrder;
        if (!order) return false;
        return !(
            order.get_partner?.()
            || order.getPartner?.()
            || order.partner
            || order.partner_id
        );
    } catch (e) {
        console.warn("[pos_require_customer] customer check error:", e);
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

patch(ProductScreen.prototype, {

    setup() {
        super.setup(...arguments);
        this._rcDialog = useService("dialog");
        const pos = this.pos;
        const dialog = this._rcDialog;

        console.log("[pos_require_customer] ProductScreen setup v12");

        if (pos?.validateOrderFast && !pos.__rc_validate_fast_wrapped__) {
            const orig = pos.validateOrderFast.bind(pos);
            pos.validateOrderFast = async (...args) => {
                if (noCustomer(pos)) {
                    await showPopup(dialog, "Please select a customer before payment.");
                    return;
                }
                return orig(...args);
            };
            pos.__rc_validate_fast_wrapped__ = true;
        }

        if (pos?.pay && !pos.__rc_pay_wrapped__) {
            const orig = pos.pay.bind(pos);
            pos.pay = async (...args) => {
                if (noCustomer(pos)) {
                    await showPopup(dialog, "Please select a customer before payment.");
                    return;
                }
                return orig(...args);
            };
            pos.__rc_pay_wrapped__ = true;
        }
    },

    async fastValidate(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before payment.");
            return;
        }
        return super.fastValidate(paymentMethod);
    },

    async selectPaymentMethod(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before payment.");
            return;
        }
        return super.selectPaymentMethod?.(...arguments);
    },

    async addPayment(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before payment.");
            return;
        }
        return super.addPayment?.(...arguments);
    },

});

patch(PaymentScreen.prototype, {

    setup() {
        super.setup(...arguments);
        this._rcDialog = useService("dialog");
        console.log("[pos_require_customer] PaymentScreen setup v12");
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

    async addPaymentLine(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before adding payment.");
            return;
        }
        return super.addPaymentLine?.(...arguments);
    },

    async addPayment(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before payment.");
            return;
        }
        return super.addPayment?.(...arguments);
    },

});
