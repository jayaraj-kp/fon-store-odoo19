/** @odoo-module */

console.log("[pos_require_customer] v11 - fastValidate fix loaded");

odoo.define('@pos_require_customer/js/require_customer', [
    '@web/core/utils/patch',
    '@web/core/utils/hooks',
    '@odoo/owl',
    '@point_of_sale/app/screens/payment_screen/payment_screen',
    '@point_of_sale/app/screens/product_screen/product_screen',
], function (require) {
    'use strict';

    let __exports = {};

    const { patch } = require("@web/core/utils/patch");
    const { useService } = require("@web/core/utils/hooks");
    const { Component } = require("@odoo/owl");
    const { PaymentScreen } = require("@point_of_sale/app/screens/payment_screen/payment_screen");
    const { ProductScreen } = require("@point_of_sale/app/screens/product_screen/product_screen");

    // ─── Dialog Component ────────────────────────────────────────────────────────

    const CustomerRequiredDialog = __exports.CustomerRequiredDialog = class CustomerRequiredDialog extends Component {
        static template = "pos_require_customer.CustomerRequiredDialog";
        static props = {
            title: { type: String, optional: true },
            body: { type: String, optional: true },
            close: { type: Function, optional: true },
        };
        confirm() {
            this.props.close?.();
        }
    };

    // ─── Helpers ─────────────────────────────────────────────────────────────────

    function noCustomer(pos) {
        try {
            const order = pos?.get_order?.()
                || pos?.getOrder?.()
                || pos?.selectedOrder
                || pos?.currentOrder;
            if (!order) return false;
            return !(
                order.get_partner?.()
                || order.getPartner?.()
                || order.partner
                || order.partner_id
            );
        } catch (e) {
            console.warn("[pos_require_customer] customer check error:", e);
            return false;
        }
    }

    async function showPopup(dialogService, body) {
        return new Promise((resolve) => {
            dialogService.add(CustomerRequiredDialog, {
                title: "Customer Required",
                body,
                close: resolve,
            });
        });
    }

    // ─── ProductScreen Patch ──────────────────────────────────────────────────────

    patch(ProductScreen.prototype, {

        setup() {
            super.setup(...arguments);
            this._rcDialog = useService("dialog");
            const pos = this.pos;
            const dialog = this._rcDialog;

            console.log("[pos_require_customer] ProductScreen setup - wrapping pos methods");

            // Wrap pos.pay
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

            // Wrap pos.validateOrderFast  ← THIS IS THE KEY FIX
            if (pos?.validateOrderFast && !pos.__rc_validate_fast_wrapped__) {
                const orig = pos.validateOrderFast.bind(pos);
                pos.validateOrderFast = async (...args) => {
                    if (noCustomer(pos)) {
                        await showPopup(dialog, "Please select a customer before payment.");
                        return;
                    }
                    return orig(...args);
                };
                pos.__rc_validate_fast_wrapped__ = true;
            }

            // Wrap pos.createPaymentLine
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

            // Wrap order-level methods
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

        // ── THE CRITICAL MISSING METHOD ──────────────────────────────────────────
        // fast-pay buttons (Cash KDTY / Card KDTY) call THIS method directly.
        // Chain: button click → fastValidate(paymentMethod) → pos.validateOrderFast()
        async fastValidate(paymentMethod) {
            if (noCustomer(this.pos)) {
                await showPopup(this._rcDialog, "Please select a customer before payment.");
                return;
            }
            return super.fastValidate(paymentMethod);
        },

        // ── Additional safety patches ────────────────────────────────────────────
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

    // ─── PaymentScreen Patch ──────────────────────────────────────────────────────

    patch(PaymentScreen.prototype, {

        setup() {
            super.setup(...arguments);
            this._rcDialog = useService("dialog");
            const pos = this.pos;
            const dialog = this._rcDialog;

            console.log("[pos_require_customer] PaymentScreen setup - wrapping order methods");

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

    return __exports;
});