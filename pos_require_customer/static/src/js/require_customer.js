/** @odoo-module **/

/**
 * POS Require Customer - Odoo 19 CE Compatible
 *
 * Uses only core OWL + @web imports to avoid broken POS internal paths.
 * The popup is a plain OWL dialog rendered via the 'dialog' service.
 */

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { Component, xml } from "@odoo/owl";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

// ─────────────────────────────────────────────────────
//  Simple Alert Dialog Component (no POS dependencies)
// ─────────────────────────────────────────────────────
export class CustomerRequiredDialog extends Component {
    static template = "pos_require_customer.CustomerRequiredDialog";
    static props = {
        title: { type: String, optional: true },
        body: { type: String, optional: true },
        close: Function,
    };
    static defaultProps = {
        title: "Customer Required",
        body: "Please select a customer before proceeding with payment.",
    };

    confirm() {
        this.props.close();
    }
}

// ─────────────────────────────────────────────────────
//  Patch ProductScreen
//  Blocks Cash KDTY / Card KDTY shortcut buttons
// ─────────────────────────────────────────────────────
patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
    },

    _isCustomerRequired() {
        try {
            const order = this.pos.get_order();
            return !order || !order.get_partner();
        } catch {
            return false;
        }
    },

    _showCustomerRequiredDialog(methodName) {
        this.dialog.add(CustomerRequiredDialog, {
            title: "Customer Required",
            body:
                "Please select a customer before using the '" +
                (methodName || "payment method") +
                "' button.",
        });
    },

    // Odoo 17/18/19 method name for shortcut payment buttons
    async clickPaymentMethod(paymentMethod) {
        if (this._isCustomerRequired()) {
            this._showCustomerRequiredDialog(paymentMethod?.name);
            return;
        }
        return super.clickPaymentMethod(...arguments);
    },
});

// ─────────────────────────────────────────────────────
//  Patch PaymentScreen
//  Blocks the main Validate / Payment button
// ─────────────────────────────────────────────────────
patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
    },

    async validateOrder(isForceValidate) {
        try {
            const order = this.pos.get_order();
            if (!order || !order.get_partner()) {
                this.dialog.add(CustomerRequiredDialog, {
                    title: "Customer Required",
                    body: "Please select a customer before completing this payment.",
                });
                return;
            }
        } catch {
            // If order check fails, allow through to avoid blocking POS
        }
        return super.validateOrder(...arguments);
    },
});
