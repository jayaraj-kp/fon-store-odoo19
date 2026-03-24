/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";

// ─────────────────────────────────────────────
//  Popup Component
// ─────────────────────────────────────────────
export class CustomerRequiredPopup extends AbstractAwaitablePopup {
    static template = "pos_require_customer.CustomerRequiredPopup";
    static defaultProps = {
        confirmText: "OK",
        title: "Customer Required",
        body: "Please select a customer before proceeding with payment.",
    };
}

// ─────────────────────────────────────────────
//  Helper: show popup and return true if blocked
// ─────────────────────────────────────────────
async function checkCustomer(pos, popup, message) {
    const order = pos.get_order();
    if (!order || !order.get_partner()) {
        await popup.add(CustomerRequiredPopup, {
            title: "Customer Required",
            body: message,
        });
        return true; // blocked
    }
    return false; // allowed
}

// ─────────────────────────────────────────────
//  Patch ProductScreen
//  Intercepts the shortcut payment buttons
//  (Cash KDTY / Card KDTY) on the order screen
// ─────────────────────────────────────────────
patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
        this.popup = useService("popup");
    },

    // Called when cashier clicks a payment method shortcut button
    async clickPaymentMethod(paymentMethod) {
        const blocked = await checkCustomer(
            this.pos,
            this.popup,
            "Please select a customer before using the '" +
                (paymentMethod.name || "payment") +
                "' method."
        );
        if (blocked) return;
        return super.clickPaymentMethod(...arguments);
    },

    // Fallback: some Odoo versions use this method name
    async selectPaymentMethod(paymentMethod) {
        if (super.selectPaymentMethod) {
            const blocked = await checkCustomer(
                this.pos,
                this.popup,
                "Please select a customer before using the '" +
                    (paymentMethod.name || "payment") +
                    "' method."
            );
            if (blocked) return;
            return super.selectPaymentMethod(...arguments);
        }
    },
});

// ─────────────────────────────────────────────
//  Patch PaymentScreen
//  Intercepts the main "Validate / Payment" button
// ─────────────────────────────────────────────
patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
        this.popup = useService("popup");
    },

    async validateOrder(isForceValidate) {
        const blocked = await checkCustomer(
            this.pos,
            this.popup,
            "Please select a customer before completing this payment."
        );
        if (blocked) return;
        return super.validateOrder(...arguments);
    },
});
