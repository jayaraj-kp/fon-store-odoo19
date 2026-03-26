/** @odoo-module **/

/**
 * POS Require Customer v14 — Odoo 19 CE
 *
 * ROOT CAUSE CONFIRMED:
 *   ActionpadWidget does NOT have `this.pos` — it is undefined.
 *   It only exposes `this.currentOrder` directly on its prototype.
 *   So noCustomer(this.pos) was always returning false → payment allowed.
 *
 * FIX:
 *   - ActionpadWidget: check this.currentOrder directly
 *   - ProductScreen / PaymentScreen: check this.pos (they DO have it)
 */

import { patch }      from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { Component }  from "@odoo/owl";
import { PaymentScreen }  from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ProductScreen }  from "@point_of_sale/app/screens/product_screen/product_screen";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";

console.log("[pos_require_customer] v14 - currentOrder fix loaded");

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
//  noCustomer — checks order from pos service
//  Used by ProductScreen / PaymentScreen (have this.pos)
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
        console.warn("[pos_require_customer] noCustomer error:", e);
        return false;
    }
}

// ─────────────────────────────────────────────────────────
//  noCustomerOnOrder — checks order directly
//  Used by ActionpadWidget (has this.currentOrder, no this.pos)
// ─────────────────────────────────────────────────────────
function noCustomerOnOrder(order) {
    try {
        if (!order) return false;
        return !(
            order.get_partner?.() ||
            order.getPartner?.() ||
            order.partner         ||
            order.partner_id
        );
    } catch (e) {
        console.warn("[pos_require_customer] noCustomerOnOrder error:", e);
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
//  - this.pos is UNDEFINED here
//  - use this.currentOrder directly instead
// ─────────────────────────────────────────────────────────
patch(ActionpadWidget.prototype, {
    setup() {
        super.setup(...arguments);
        this._rcDialog = useService("dialog");
        console.log("[pos_require_customer] ActionpadWidget patched ✓");
    },

    /**
     * CONFIRMED FIX — "Cash KDTY" / "Card KDTY" one-click pay buttons
     * Uses this.currentOrder (not this.pos which is undefined here)
     */
    async fastValidate(paymentMethod) {
        if (noCustomerOnOrder(this.currentOrder)) {
            await showPopup(this._rcDialog, "Please select a customer before payment.");
            return;
        }
        return super.fastValidate?.(...arguments);
    },

    /** "Payment" button */
    async pay() {
        if (noCustomerOnOrder(this.currentOrder)) {
            await showPopup(this._rcDialog, "Please select a customer before payment.");
            return;
        }
        return super.pay(...arguments);
    },
});

// ─────────────────────────────────────────────────────────
//  Patch ProductScreen — this.pos IS available here
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
//  Patch PaymentScreen — final safety net
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