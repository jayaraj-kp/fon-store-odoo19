/** @odoo-module **/

/**
 * POS Require Customer v13 — Odoo 19 CE
 *
 * Root cause CONFIRMED via DOM event inspection:
 *   "Cash KDTY" / "Card KDTY" buttons call:  fastValidate(paymentMethod)
 *   "Payment" button calls:                  pay()
 *   Both are on ActionpadWidget.
 *
 * Intercepts:
 * 1. ActionpadWidget.fastValidate()  ← "Cash KDTY / Card KDTY"  ✅ CONFIRMED FIX
 * 2. ActionpadWidget.pay()           ← "Payment" button
 * 3. PaymentScreen.validateOrder()   ← Final validation safety net
 */

import { patch }      from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { Component }  from "@odoo/owl";
import { PaymentScreen }  from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ProductScreen }  from "@point_of_sale/app/screens/product_screen/product_screen";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";

console.log("[pos_require_customer] v13 - fastValidate interception loaded");

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
//  Helper — check if current order has no customer
// ─────────────────────────────────────────────────────────
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
            order.partner         ||
            order.partner_id
        );
    } catch (e) {
        console.warn("[pos_require_customer] customer check error:", e);
        return false;
    }
}

// Show the "Customer Required" popup
async function showPopup(dialogService, body) {
    return new Promise((resolve) => {
        dialogService.add(CustomerRequiredDialog, {
            title: "Customer Required",
            body,
            close: resolve,
        });
    });
}

// ─────────────────────────────────────────────────────────
//  Patch ActionpadWidget
// ─────────────────────────────────────────────────────────
patch(ActionpadWidget.prototype, {
    setup() {
        super.setup(...arguments);
        this._rcDialog = useService("dialog");
        console.log("[pos_require_customer] ActionpadWidget patched ✓");
    },

    /**
     * CONFIRMED FIX — handles "Cash KDTY" / "Card KDTY" one-click pay buttons
     * DOM event: __event__click -> ()=>v5.fastValidate(v6)
     */
    async fastValidate(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before payment.");
            return;
        }
        return super.fastValidate?.(...arguments);
    },

    /**
     * Handles the "Payment" button
     */
    async pay() {
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before payment.");
            return;
        }
        return super.pay(...arguments);
    },
});

// ─────────────────────────────────────────────────────────
//  Patch ProductScreen — guard pos.pay() at service level
// ─────────────────────────────────────────────────────────
patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this._rcDialog = useService("dialog");
        const pos    = this.pos;
        const dialog = this._rcDialog;

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
});

// ─────────────────────────────────────────────────────────
//  Patch PaymentScreen — safety net if user reaches it
// ─────────────────────────────────────────────────────────
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
});