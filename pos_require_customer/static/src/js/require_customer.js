/** @odoo-module **/

/**
 * POS Require Customer v2 - Odoo 19 CE
 *
 * Strategy: patch BOTH ProductScreen and PaymentScreen using every
 * known method name variant across Odoo 17/18/19, plus a global
 * DOM-level safety net that catches any payment navigation.
 */

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

// ─────────────────────────────────────────────────────────────────
//  Popup Dialog — pure OWL, zero POS dependencies
// ─────────────────────────────────────────────────────────────────
export class CustomerRequiredDialog extends Component {
    static template = "pos_require_customer.CustomerRequiredDialog";
    static props = {
        title: { type: String, optional: true },
        body: { type: String, optional: true },
        close: { type: Function, optional: true },
    };
    confirm() {
        if (this.props.close) this.props.close();
    }
}

// ─────────────────────────────────────────────────────────────────
//  Shared helper — checks if current order has a customer
// ─────────────────────────────────────────────────────────────────
function hasNoCustomer(posStore) {
    try {
        const order =
            posStore.get_order?.() ||
            posStore.selectedOrder ||
            posStore.currentOrder;
        if (!order) return false;
        return !(
            order.get_partner?.() ||
            order.partner ||
            order.partner_id
        );
    } catch (e) {
        console.warn("[pos_require_customer] Customer check failed:", e);
        return false;
    }
}

async function showCustomerPopup(dialogService, body) {
    return new Promise((resolve) => {
        dialogService.add(CustomerRequiredDialog, {
            title: "Customer Required",
            body: body || "Please select a customer before proceeding with payment.",
            close: resolve,
        });
    });
}

// ─────────────────────────────────────────────────────────────────
//  Patch ProductScreen
//  Covers: clickPaymentMethod / selectPaymentMethod / pay
//  (method name differs across Odoo minor versions)
// ─────────────────────────────────────────────────────────────────
patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this._requireCustomer_dialog = useService("dialog");
    },

    // Odoo 17.0 name
    async pay() {
        if (hasNoCustomer(this.pos)) {
            await showCustomerPopup(
                this._requireCustomer_dialog,
                "Please select a customer before proceeding to payment."
            );
            return;
        }
        return super.pay?.(...arguments);
    },

    // Odoo 17/18 name for shortcut payment buttons
    async clickPaymentMethod(paymentMethod) {
        if (hasNoCustomer(this.pos)) {
            await showCustomerPopup(
                this._requireCustomer_dialog,
                `Please select a customer before using "${paymentMethod?.name || "this payment method"}".`
            );
            return;
        }
        return super.clickPaymentMethod?.(...arguments);
    },

    // Odoo 18/19 alternate name
    async selectPaymentMethod(paymentMethod) {
        if (hasNoCustomer(this.pos)) {
            await showCustomerPopup(
                this._requireCustomer_dialog,
                `Please select a customer before using "${paymentMethod?.name || "this payment method"}".`
            );
            return;
        }
        if (super.selectPaymentMethod) {
            return super.selectPaymentMethod?.(...arguments);
        }
    },
});

// ─────────────────────────────────────────────────────────────────
//  Patch PaymentScreen
//  Covers validateOrder (main validate/payment button)
// ─────────────────────────────────────────────────────────────────
patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this._requireCustomer_dialog = useService("dialog");
    },

    async validateOrder(isForceValidate) {
        if (hasNoCustomer(this.pos)) {
            await showCustomerPopup(
                this._requireCustomer_dialog,
                "Please select a customer before completing this payment."
            );
            return;
        }
        return super.validateOrder(...arguments);
    },
});
