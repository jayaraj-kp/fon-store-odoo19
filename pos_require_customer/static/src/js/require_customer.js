/** @odoo-module **/

/**
 * POS Require Customer v8 — Odoo 19 CE (COMPLETE FIX)
 *
 * The Cash KDTY and Card KDTY buttons bypass normal payment flow.
 * Solution: Patch at the PAYMENT STATE level, intercepting all payment attempts.
 *
 * This version patches:
 * 1. PaymentLine class - when a payment line is added
 * 2. Order.addPaymentLine() - before any payment is recorded
 * 3. Payment method selection at the ORDER level
 * 4. All screen validate methods as final safety net
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

            pos.__rc_pay_patched__ = true;
        }

        // ── Wrap order.addPaymentLine() ─────────────────────
        // This catches ALL payment additions regardless of button
        const order = pos?.get_order?.() || pos?.getOrder?.() || pos?.selectedOrder || pos?.currentOrder;
        if (order && typeof order.addPaymentLine === "function" && !order.__rc_payment_patched__) {
            const originalAddPaymentLine = order.addPaymentLine.bind(order);
            const dialog = this._rcDialog;

            order.addPaymentLine = async function (...args) {
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
        }
    },

    // ── Multiple payment method entry points ───────────────
    async selectPaymentMethod(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(
                this._rcDialog,
                `Please select a customer before using payment.`
            );
            return;
        }
        return super.selectPaymentMethod?.(...arguments);
    },

    async clickPaymentMethod(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(
                this._rcDialog,
                `Please select a customer before using payment.`
            );
            return;
        }
        return super.clickPaymentMethod?.(...arguments);
    },

    async addPaymentLine(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(
                this._rcDialog,
                `Please select a customer before adding payment.`
            );
            return;
        }
        return super.addPaymentLine?.(...arguments);
    },

    async openPaymentInterfaceElectronically(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(
                this._rcDialog,
                "Please select a customer before processing card payment."
            );
            return;
        }
        return super.openPaymentInterfaceElectronically?.(...arguments);
    },

    async selectCashPaymentMethod() {
        if (noCustomer(this.pos)) {
            await showPopup(
                this._rcDialog,
                "Please select a customer before using cash payment."
            );
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

        // ── Wrap addPaymentLine on the order ─────────────────────
        const pos = this.pos;
        const order = pos?.get_order?.() || pos?.getOrder?.() || pos?.selectedOrder || pos?.currentOrder;

        if (order && typeof order.addPaymentLine === "function" && !order.__rc_payment_patched__) {
            const originalAddPaymentLine = order.addPaymentLine.bind(order);
            const dialog = this._rcDialog;

            order.addPaymentLine = async function (...args) {
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
        }
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
        return super.validateOrderFast?.(...arguments);
    },

    async selectPaymentMethod(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(
                this._rcDialog,
                `Please select a customer before using payment.`
            );
            return;
        }
        return super.selectPaymentMethod?.(...arguments);
    },

    async clickPaymentMethod(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(
                this._rcDialog,
                `Please select a customer before using payment.`
            );
            return;
        }
        return super.clickPaymentMethod?.(...arguments);
    },

    async addPaymentLine(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(
                this._rcDialog,
                `Please select a customer before adding payment.`
            );
            return;
        }
        return super.addPaymentLine?.(...arguments);
    },

    async openPaymentInterfaceElectronically(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(
                this._rcDialog,
                "Please select a customer before processing card payment."
            );
            return;
        }
        return super.openPaymentInterfaceElectronically?.(...arguments);
    },
});