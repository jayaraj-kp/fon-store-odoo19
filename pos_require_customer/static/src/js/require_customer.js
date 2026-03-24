/** @odoo-module **/

/**
 * POS Require Customer v4 — Odoo 19 CE
 *
 * ROOT CAUSE CONFIRMED from live bundle:
 *   The Payment button template calls:  actionToTrigger="() => pos.pay()"
 *   So we must patch the PosStore (pos), NOT ProductScreen.
 *
 * Also confirmed from bundle:
 *   Cash/Card shortcut buttons call:   async clickPaymentMethod()  on ProductScreen
 *   Validate button calls:             async validateOrder()        on PaymentScreen
 *   Fast validate calls:               async validateOrderFast()    on PaymentScreen
 */

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

// ─────────────────────────────────────────────────────────
//  Popup — pure OWL, no POS inheritance
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
//  Helper — true when current order has no customer
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

// Show popup — returns a promise that resolves when user clicks OK
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
//  1. Patch PosStore.pay()
//     The Payment button calls:  () => pos.pay()
//     This is the most critical patch.
// ─────────────────────────────────────────────────────────
patch(PosStore.prototype, {
    async pay() {
        // PosStore has no dialog service — grab it from the env
        const dialogService =
            this.env?.services?.dialog ||
            this.dialog;

        if (noCustomer(this)) {
            if (dialogService) {
                await showPopup(
                    dialogService,
                    "Please select a customer before proceeding to payment."
                );
            } else {
                // Fallback: native browser alert if dialog service unavailable
                alert("Please select a customer before proceeding to payment.");
            }
            return;
        }
        return super.pay(...arguments);
    },
});

// ─────────────────────────────────────────────────────────
//  2. Patch ProductScreen — Cash KDTY / Card KDTY buttons
//     Bundle confirmed:  async clickPaymentMethod()
// ─────────────────────────────────────────────────────────
patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this._rcDialog = useService("dialog");
    },

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
//  3. Patch PaymentScreen — Validate button (safety net)
//     In case user reaches PaymentScreen by other means.
//     Bundle confirmed:  async validateOrder()
//                        async validateOrderFast()
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
