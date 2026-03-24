/** @odoo-module **/

/**
 * POS Require Customer v7 — Odoo 19 CE
 *
 * The "Payment" button in Odoo 19 ProductScreen template calls:
 *     actionToTrigger="() => pos.pay()"
 * where `pos` is the PosStore SERVICE injected via useService("pos").
 *
 * We cannot import PosStore directly (broken path in Odoo 19).
 * Solution: inside ProductScreen.setup(), we grab the live `pos` service
 * instance and wrap its `pay` method at runtime — no import needed.
 *
 * Entry points covered:
 *   ✅ "Payment" button       → pos.pay()            (runtime wrap in setup)
 *   ✅ "Cash KDTY" button     → clickPaymentMethod()  (prototype patch)
 *   ✅ "Card KDTY" button     → clickPaymentMethod()  (prototype patch)
 *   ✅ Validate (safety net)  → validateOrder()       (PaymentScreen patch)
 *   ✅ Fast validate          → validateOrderFast()   (PaymentScreen patch)
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
// ─────────────────────────────────────────────────────────
patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this._rcDialog = useService("dialog");

        // ── Wrap pos.pay() at runtime ─────────────────────
        // The Payment button calls `() => pos.pay()` where pos is
        // the service instance. We wrap it once here so the check
        // fires regardless of which template triggers it.
        const pos = this.pos;
        if (pos && typeof pos.pay === "function" && !pos.__rc_pay_patched__) {
            const originalPay = pos.pay.bind(pos);
            const dialog = this._rcDialog;

            pos.pay = async function (...args) {
                if (noCustomer(pos)) {
                    await showPopup(
                        dialog,
                        "Please select a customer before proceeding to payment."
                    );
                    return;
                }
                return originalPay(...args);
            };

            // Mark so we only wrap once even if setup() is called again
            pos.__rc_pay_patched__ = true;
        }
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
//     Covers users who reach PaymentScreen by any other path.
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