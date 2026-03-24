/** @odoo-module **/

/**
 * POS Require Customer v6 — Odoo 19 CE
 *
 * Blocks ALL payment entry points on ProductScreen:
 *   - "Payment" button        → ProductScreen.pay()
 *   - "Cash KDTY" button      → ProductScreen.clickPaymentMethod()
 *   - "Card KDTY" button      → ProductScreen.clickPaymentMethod()
 *
 * Safety net on PaymentScreen (in case user reaches it another way):
 *   - Validate button         → PaymentScreen.validateOrder()
 *   - Fast validate           → PaymentScreen.validateOrderFast()
 */

import { patch }      from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { Component }  from "@odoo/owl";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

// ─────────────────────────────────────────────────────────
//  Dialog component
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
//  Helper — true when current order has no customer set
// ─────────────────────────────────────────────────────────
function noCustomer(pos) {
    try {
        const order =
            pos?.get_order?.()  ||
            pos?.getOrder?.()   ||
            pos?.selectedOrder  ||
            pos?.currentOrder;
        if (!order) return false;
        return !(
            order.get_partner?.() ||
            order.getPartner?.()  ||
            order.partner         ||
            order.partner_id
        );
    } catch (e) {
        console.warn("[pos_require_customer] customer check error:", e);
        return false;
    }
}

// Show popup and wait for user to press OK
function showPopup(dialogService, body) {
    return new Promise((resolve) => {
        dialogService.add(CustomerRequiredDialog, {
            title: "Customer Required",
            body,
            close: resolve,
        });
    });
}

// ─────────────────────────────────────────────────────────
//  1. Patch ProductScreen
//     Covers:
//       • "Payment" button        → pay()
//       • "Cash KDTY" button      → clickPaymentMethod()
//       • "Card KDTY" button      → clickPaymentMethod()
// ─────────────────────────────────────────────────────────
patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this._rcDialog = useService("dialog");
    },

    // ── "Payment" button ─────────────────────────────────
    async pay() {
        if (noCustomer(this.pos)) {
            await showPopup(
                this._rcDialog,
                "Please select a customer before proceeding to payment."
            );
            return;
        }
        return super.pay(...arguments);
    },

    // ── "Cash KDTY" / "Card KDTY" shortcut buttons ───────
    async clickPaymentMethod(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(
                this._rcDialog,
                `Please select a customer before using "${paymentMethod?.name || "this payment method"}".`
            );
            return;
        }
        return super.clickPaymentMethod(...arguments);
    },
});

// ─────────────────────────────────────────────────────────
//  2. Patch PaymentScreen — safety net
//     In case user somehow reaches PaymentScreen directly.
// ─────────────────────────────────────────────────────────
patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this._rcDialog = useService("dialog");
    },

    async validateOrder(isForceValidate) {
        if (noCustomer(this.pos)) {
            await showPopup(
                this._rcDialog,
                "Please select a customer before completing this payment."
            );
            return;
        }
        return super.validateOrder(...arguments);
    },

    async validateOrderFast() {
        if (noCustomer(this.pos)) {
            await showPopup(
                this._rcDialog,
                "Please select a customer before completing this payment."
            );
            return;
        }
        return super.validateOrderFast(...arguments);
    },
});