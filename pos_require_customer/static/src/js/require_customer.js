/** @odoo-module **/

/**
 * POS Require Customer v11 — Odoo 19 CE
 *
 * Intercepts payment at ALL entry points:
 * 1. ActionpadWidget.pay()              ← "Payment" button
 * 2. ActionpadWidget.clickPaymentMethod() ← "Cash KDTY / Card KDTY" direct buttons  ✅ NEW
 * 3. ProductScreen payment methods
 * 4. PaymentScreen validation + payment methods
 * 5. pos.pay() / order method wrappers
 */

import { patch }      from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { Component }  from "@odoo/owl";
import { PaymentScreen }  from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ProductScreen }  from "@point_of_sale/app/screens/product_screen/product_screen";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";

console.log("[pos_require_customer] v11 - ActionpadWidget interception loaded");

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
//  Helper — check customer on current order
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

// Show the red "Customer Required" popup
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
//  This is the component that renders:
//    • the "Payment" button
//    • direct payment buttons like "Cash KDTY", "Card KDTY"
// ─────────────────────────────────────────────────────────
patch(ActionpadWidget.prototype, {
    setup() {
        super.setup(...arguments);
        this._rcDialog = useService("dialog");
        console.log("[pos_require_customer] ActionpadWidget patched");
    },

    /** Called when the big "Payment" button is clicked */
    async pay() {
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before payment.");
            return;
        }
        return super.pay(...arguments);
    },

    /**
     * Called when a direct payment-method button is clicked
     * (e.g. "Cash KDTY", "Card KDTY" shown at the bottom of the product screen)
     */
    async clickPaymentMethod(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(
                this._rcDialog,
                "Please select a customer before payment."
            );
            return;
        }
        return super.clickPaymentMethod?.(...arguments);
    },

    // Extra aliases used in some Odoo 19 builds
    async selectPaymentMethod(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before payment.");
            return;
        }
        return super.selectPaymentMethod?.(...arguments);
    },

    async addPaymentLine(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before payment.");
            return;
        }
        return super.addPaymentLine?.(...arguments);
    },
});

// ─────────────────────────────────────────────────────────
//  Patch ProductScreen — secondary guard
// ─────────────────────────────────────────────────────────
patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this._rcDialog = useService("dialog");
        const pos    = this.pos;
        const dialog = this._rcDialog;

        // Wrap pos.pay() at the service level
        if (pos?.pay && !pos.__rc_pay_wrapped__) {
            const orig  = pos.pay.bind(pos);
            pos.pay = async (...args) => {
                if (noCustomer(pos)) {
                    await showPopup(dialog, "Please select a customer before payment.");
                    return;
                }
                return orig(...args);
            };
            pos.__rc_pay_wrapped__ = true;
        }

        // Wrap pos.createPaymentLine() if present
        if (pos?.createPaymentLine && !pos.__rc_create_payment_line_wrapped__) {
            const orig  = pos.createPaymentLine.bind(pos);
            pos.createPaymentLine = async (...args) => {
                if (noCustomer(pos)) {
                    await showPopup(dialog, "Please select a customer before adding payment.");
                    return false;
                }
                return orig(...args);
            };
            pos.__rc_create_payment_line_wrapped__ = true;
        }

        // Wrap current order instance methods
        const order = pos?.get_order?.() || pos?.getOrder?.() || pos?.selectedOrder;
        if (order) {
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
        }
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

    async addPayment(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before payment.");
            return;
        }
        return super.addPayment?.(...arguments);
    },
});

// ─────────────────────────────────────────────────────────
//  Patch PaymentScreen — final safety net
// ─────────────────────────────────────────────────────────
patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this._rcDialog = useService("dialog");
        const pos    = this.pos;
        const dialog = this._rcDialog;

        const order = pos?.get_order?.() || pos?.getOrder?.() || pos?.selectedOrder;
        if (order) {
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

    async addPayment(paymentMethod) {
        if (noCustomer(this.pos)) {
            await showPopup(this._rcDialog, "Please select a customer before payment.");
            return;
        }
        return super.addPayment?.(...arguments);
    },
});