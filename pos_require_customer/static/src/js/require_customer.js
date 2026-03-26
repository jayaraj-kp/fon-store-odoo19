/** @odoo-module **/

/**
 * POS Require Customer v10 — Odoo 19 CE (ADVANCED INTERCEPTION)
 *
 * Some payment methods might bypass JS methods entirely by making RPC calls.
 * Solution: Wrap the POS order model itself and intercept at multiple levels:
 * 1. Order.createPaymentLine()
 * 2. Order.addPaymentLine()
 * 3. pos.selectedOrder property setter
 * 4. All Screen payment methods
 * 5. pos.createPaymentLine() if it exists
 */

import { patch }      from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { Component }  from "@odoo/owl";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

console.log("[pos_require_customer] v10 - Advanced interception loaded");

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
//  Helper — check customer
// ─────────────────────────────────────────────────────────
function noCustomer(pos) {
    try {
        const order = pos?.get_order?.() || pos?.getOrder?.() || pos?.selectedOrder || pos?.currentOrder;
        if (!order) return false;
        return !(order.get_partner?.() || order.getPartner?.() || order.partner || order.partner_id);
    } catch (e) {
        console.warn("[pos_require_customer] customer check error:", e);
        return false;
    }
}

// Show dialog
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
//  Patch ProductScreen - Main Entry
// ─────────────────────────────────────────────────────────
patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this._rcDialog = useService("dialog");
        const pos = this.pos;
        const dialog = this._rcDialog;

        console.log("[pos_require_customer] ProductScreen setup - wrapping pos methods");

        // 1. Wrap pos.pay()
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

        // 2. Wrap pos.createPaymentLine() if it exists
        if (pos?.createPaymentLine && !pos.__rc_create_payment_line_wrapped__) {
            const orig = pos.createPaymentLine.bind(pos);
            pos.createPaymentLine = async (...args) => {
                if (noCustomer(pos)) {
                    await showPopup(dialog, "Please select a customer before adding payment.");
                    return false;
                }
                return orig(...args);
            };
            pos.__rc_create_payment_line_wrapped__ = true;
        }

        // 3. Wrap order methods
        const order = pos?.get_order?.() || pos?.getOrder?.() || pos?.selectedOrder;
        if (order) {
            // Wrap addPaymentLine
            if (order.addPaymentLine && !order.__rc_add_payment_wrapped__) {
                const orig = order.addPaymentLine.bind(order);
                order.addPaymentLine = async (...args) => {
                    if (noCustomer(pos)) {
                        await showPopup(dialog, "Please select a customer before adding payment.");
                        return false;
                    }
                    return orig(...args);
                };
                order.__rc_add_payment_wrapped__ = true;
            }

            // Wrap createPaymentLine if exists
            if (order.createPaymentLine && !order.__rc_create_payment_wrapped__) {
                const orig = order.createPaymentLine.bind(order);
                order.createPaymentLine = async (...args) => {
                    if (noCustomer(pos)) {
                        await showPopup(dialog, "Please select a customer before adding payment.");
                        return false;
                    }
                    return orig(...args);
                };
                order.__rc_create_payment_wrapped__ = true;
            }

            // Wrap payment() method if exists
            if (order.payment && !order.__rc_payment_wrapped__) {
                const orig = order.payment.bind(order);
                order.payment = async (...args) => {
                    if (noCustomer(pos)) {
                        await showPopup(dialog, "Please select a customer before payment.");
                        return false;
                    }
                    return orig(...args);
                };
                order.__rc_payment_wrapped__ = true;
            }
        }
    },

    // Screen-level payment methods
    async selectPaymentMethod(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before payment.");
            return;
        }
        return super.selectPaymentMethod?.(...arguments);
    },

    async clickPaymentMethod(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before payment.");
            return;
        }
        return super.clickPaymentMethod?.(...arguments);
    },

    async addPaymentLine(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before adding payment.");
            return;
        }
        return super.addPaymentLine?.(...arguments);
    },

    async createPaymentLine(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before creating payment.");
            return;
        }
        return super.createPaymentLine?.(...arguments);
    },

    async openPaymentInterfaceElectronically(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before card payment.");
            return;
        }
        return super.openPaymentInterfaceElectronically?.(...arguments);
    },

    async selectCashPaymentMethod() {
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before cash payment.");
            return;
        }
        return super.selectCashPaymentMethod?.(...arguments);
    },

    // Generic catch-all: wrap any method that includes "payment"
    async onClickPaymentButton(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before payment.");
            return;
        }
        return super.onClickPaymentButton?.(...arguments);
    },

    async addPayment(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before payment.");
            return;
        }
        return super.addPayment?.(...arguments);
    },
});

// ─────────────────────────────────────────────────────────
//  Patch PaymentScreen - Safety Net
// ─────────────────────────────────────────────────────────
patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this._rcDialog = useService("dialog");
        const pos = this.pos;
        const dialog = this._rcDialog;

        console.log("[pos_require_customer] PaymentScreen setup - wrapping order methods");

        const order = pos?.get_order?.() || pos?.getOrder?.() || pos?.selectedOrder;
        if (order) {
            // Wrap addPaymentLine
            if (order.addPaymentLine && !order.__rc_add_payment_ps_wrapped__) {
                const orig = order.addPaymentLine.bind(order);
                order.addPaymentLine = async (...args) => {
                    if (noCustomer(pos)) {
                        await showPopup(dialog, "Please select a customer before adding payment.");
                        return false;
                    }
                    return orig(...args);
                };
                order.__rc_add_payment_ps_wrapped__ = true;
            }

            // Wrap createPaymentLine
            if (order.createPaymentLine && !order.__rc_create_payment_ps_wrapped__) {
                const orig = order.createPaymentLine.bind(order);
                order.createPaymentLine = async (...args) => {
                    if (noCustomer(pos)) {
                        await showPopup(dialog, "Please select a customer before creating payment.");
                        return false;
                    }
                    return orig(...args);
                };
                order.__rc_create_payment_ps_wrapped__ = true;
            }
        }
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

    async selectPaymentMethod(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before payment.");
            return;
        }
        return super.selectPaymentMethod?.(...arguments);
    },

    async clickPaymentMethod(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before payment.");
            return;
        }
        return super.clickPaymentMethod?.(...arguments);
    },

    async addPaymentLine(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before adding payment.");
            return;
        }
        return super.addPaymentLine?.(...arguments);
    },

    async createPaymentLine(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before creating payment.");
            return;
        }
        return super.createPaymentLine?.(...arguments);
    },

    async openPaymentInterfaceElectronically(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before card payment.");
            return;
        }
        return super.openPaymentInterfaceElectronically?.(...arguments);
    },

    async onClickPaymentButton(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before payment.");
            return;
        }
        return super.onClickPaymentButton?.(...arguments);
    },

    async addPayment(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before payment.");
            return;
        }
        return super.addPayment?.(...arguments);
    },
});