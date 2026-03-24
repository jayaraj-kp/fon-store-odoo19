/** @odoo-module **/

/**
 * POS Require Customer v3 — Odoo 19 CE
 * Confirmed method names from live bundle:
 *   ProductScreen : async pay()
 *   ProductScreen : async clickPaymentMethod()   ← Cash KDTY / Card KDTY
 *   PaymentScreen : async validateOrder()
 *   PaymentScreen : async validateOrderFast()
 */

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

// ─────────────────────────────────────────────────────────
//  Popup — pure OWL Component, no POS inheritance needed
// ─────────────────────────────────────────────────────────
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

// ─────────────────────────────────────────────────────────
//  Helper — returns true if no customer on current order
// ─────────────────────────────────────────────────────────
function noCustomer(pos) {
    try {
        const order =
            pos?.get_order?.()      ||
            pos?.selectedOrder      ||
            pos?.currentOrder;
        if (!order) return false;
        return !(order.get_partner?.() || order.partner || order.partner_id);
    } catch (e) {
        console.warn("[pos_require_customer] customer check error:", e);
        return false;
    }
}

async function warnNoCustomer(dialogService, body) {
    return new Promise((resolve) => {
        dialogService.add(CustomerRequiredDialog, {
            title: "Customer Required",
            body,
            close: resolve,
        });
    });
}

// ─────────────────────────────────────────────────────────
//  Patch ProductScreen
//  • async pay()               — "Payment" button (goes to PaymentScreen)
//  • async clickPaymentMethod()— "Cash KDTY" / "Card KDTY" shortcut buttons
// ─────────────────────────────────────────────────────────
patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this._rcDialog = useService("dialog");
    },

    async pay() {
        if (noCustomer(this.pos)) {
            await warnNoCustomer(
                this._rcDialog,
                "Please select a customer before proceeding to payment."
            );
            return;
        }
        return super.pay(...arguments);
    },

    async clickPaymentMethod(paymentMethod) {
        if (noCustomer(this.pos)) {
            await warnNoCustomer(
                this._rcDialog,
                `Please select a customer before using "${paymentMethod?.name || "this payment method"}".`
            );
            return;
        }
        return super.clickPaymentMethod(...arguments);
    },
});

// ─────────────────────────────────────────────────────────
//  Patch PaymentScreen
//  • async validateOrder()     — main Validate button
//  • async validateOrderFast() — fast-pay shortcut
// ─────────────────────────────────────────────────────────
patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this._rcDialog = useService("dialog");
    },

    async validateOrder(isForceValidate) {
        if (noCustomer(this.pos)) {
            await warnNoCustomer(
                this._rcDialog,
                "Please select a customer before completing this payment."
            );
            return;
        }
        return super.validateOrder(...arguments);
    },

    async validateOrderFast() {
        if (noCustomer(this.pos)) {
            await warnNoCustomer(
                this._rcDialog,
                "Please select a customer before completing this payment."
            );
            return;
        }
        return super.validateOrderFast(...arguments);
    },
});
