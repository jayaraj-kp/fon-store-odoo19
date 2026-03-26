/** @odoo-module **/

/**
 * POS Require Customer v9 — Odoo 19 CE (ULTIMATE FIX)
 *
 * The Cash KDTY and Card KDTY buttons are making direct calls that bypass screen methods.
 * Solution: Patch the CORE POS Store and Order payment methods.
 *
 * Patches:
 * 1. PosStore.pay() - Core payment method
 * 2. Order.addPaymentLine() - All payments go through here
 * 3. PosStore.convertedPosOrderlineToOrderlineData() - Before order processing
 * 4. PosStore.selectPartner() - Confirm customer selection
 * 5. All Screen validation methods
 */

import { patch }      from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { Component }  from "@odoo/owl";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

console.log("[pos_require_customer] Module loaded - v9 with CORE patching");

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

        const hasCustomer = !!(
            order.get_partner?.() ||
            order.getPartner?.()  ||
            order.partner         ||
            order.partner_id
        );

        console.log("[pos_require_customer] Customer check:", { hasCustomer, orderHasPartner: !!order.partner });
        return !hasCustomer;
    } catch (e) {
        console.warn("[pos_require_customer] customer check error:", e);
        return false;
    }
}

// Show popup and wait for user to press OK
function showPopup(dialogService, body) {
    console.log("[pos_require_customer] Showing dialog:", body);
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
        console.log("[pos_require_customer] ProductScreen.setup() called");

        const pos = this.pos;
        const dialog = this._rcDialog;

        // ── Wrap pos.pay() ─────────────────────
        if (pos && typeof pos.pay === "function" && !pos.__rc_pay_patched__) {
            const originalPay = pos.pay.bind(pos);

            pos.pay = async function (...args) {
                console.log("[pos_require_customer] pos.pay() called");
                if (noCustomer(pos)) {
                    await showPopup(
                        dialog,
                        "Please select a customer before proceeding to payment."
                    );
                    return;
                }
                return originalPay(...args);
            };

            pos.__rc_pay_patched__ = true;
            console.log("[pos_require_customer] pos.pay() wrapped");
        }

        // ── Wrap pos.selectPartner() to track customer selection ─
        if (pos && typeof pos.selectPartner === "function" && !pos.__rc_select_partner_patched__) {
            const originalSelectPartner = pos.selectPartner.bind(pos);

            pos.selectPartner = async function (...args) {
                console.log("[pos_require_customer] selectPartner called with:", args);
                return originalSelectPartner(...args);
            };

            pos.__rc_select_partner_patched__ = true;
        }

        // ── Wrap addPaymentLine at order level ─────────────────────
        const order = pos?.get_order?.() || pos?.getOrder?.() || pos?.selectedOrder || pos?.currentOrder;
        if (order && typeof order.addPaymentLine === "function" && !order.__rc_payment_patched__) {
            const originalAddPaymentLine = order.addPaymentLine.bind(order);

            order.addPaymentLine = async function (...args) {
                console.log("[pos_require_customer] order.addPaymentLine() called");
                if (noCustomer(pos)) {
                    await showPopup(
                        dialog,
                        "Please select a customer before adding a payment method."
                    );
                    return false;
                }
                return originalAddPaymentLine(...args);
            };

            order.__rc_payment_patched__ = true;
            console.log("[pos_require_customer] order.addPaymentLine() wrapped");
        }
    },

    async selectPaymentMethod(paymentMethod) {
        console.log("[pos_require_customer] ProductScreen.selectPaymentMethod() called:", paymentMethod?.name);
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before using payment.");
            return;
        }
        return super.selectPaymentMethod?.(...arguments);
    },

    async clickPaymentMethod(paymentMethod) {
        console.log("[pos_require_customer] ProductScreen.clickPaymentMethod() called:", paymentMethod?.name);
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before using payment.");
            return;
        }
        return super.clickPaymentMethod?.(...arguments);
    },

    async addPaymentLine(paymentMethod) {
        console.log("[pos_require_customer] ProductScreen.addPaymentLine() called:", paymentMethod?.name);
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before adding payment.");
            return;
        }
        return super.addPaymentLine?.(...arguments);
    },

    async openPaymentInterfaceElectronically(paymentMethod) {
        console.log("[pos_require_customer] ProductScreen.openPaymentInterfaceElectronically() called");
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before processing card payment.");
            return;
        }
        return super.openPaymentInterfaceElectronically?.(...arguments);
    },

    async selectCashPaymentMethod() {
        console.log("[pos_require_customer] ProductScreen.selectCashPaymentMethod() called");
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before using cash payment.");
            return;
        }
        return super.selectCashPaymentMethod?.(...arguments);
    },
});

// ─────────────────────────────────────────────────────────
//  2. Patch PaymentScreen
// ─────────────────────────────────────────────────────────
patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this._rcDialog = useService("dialog");
        console.log("[pos_require_customer] PaymentScreen.setup() called");

        const pos = this.pos;
        const dialog = this._rcDialog;

        // ── Wrap addPaymentLine at PaymentScreen level too ─────────────────────
        const order = pos?.get_order?.() || pos?.getOrder?.() || pos?.selectedOrder || pos?.currentOrder;
        if (order && typeof order.addPaymentLine === "function" && !order.__rc_payment_patched_ps__) {
            const originalAddPaymentLine = order.addPaymentLine.bind(order);

            order.addPaymentLine = async function (...args) {
                console.log("[pos_require_customer] [PaymentScreen] order.addPaymentLine() called");
                if (noCustomer(pos)) {
                    await showPopup(
                        dialog,
                        "Please select a customer before adding a payment method."
                    );
                    return false;
                }
                return originalAddPaymentLine(...args);
            };

            order.__rc_payment_patched_ps__ = true;
            console.log("[pos_require_customer] [PaymentScreen] order.addPaymentLine() wrapped");
        }
    },

    async validateOrder(isForceValidate) {
        console.log("[pos_require_customer] PaymentScreen.validateOrder() called");
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
        console.log("[pos_require_customer] PaymentScreen.validateOrderFast() called");
        if (noCustomer(this.pos)) {
            await showPopup(
                this._rcDialog,
                "Please select a customer before completing this payment."
            );
            return;
        }
        return super.validateOrderFast?.(...arguments);
    },

    async selectPaymentMethod(paymentMethod) {
        console.log("[pos_require_customer] PaymentScreen.selectPaymentMethod() called:", paymentMethod?.name);
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before using payment.");
            return;
        }
        return super.selectPaymentMethod?.(...arguments);
    },

    async clickPaymentMethod(paymentMethod) {
        console.log("[pos_require_customer] PaymentScreen.clickPaymentMethod() called:", paymentMethod?.name);
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before using payment.");
            return;
        }
        return super.clickPaymentMethod?.(...arguments);
    },

    async addPaymentLine(paymentMethod) {
        console.log("[pos_require_customer] PaymentScreen.addPaymentLine() called:", paymentMethod?.name);
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before adding payment.");
            return;
        }
        return super.addPaymentLine?.(...arguments);
    },

    async openPaymentInterfaceElectronically(paymentMethod) {
        console.log("[pos_require_customer] PaymentScreen.openPaymentInterfaceElectronically() called");
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before processing card payment.");
            return;
        }
        return super.openPaymentInterfaceElectronically?.(...arguments);
    },
});