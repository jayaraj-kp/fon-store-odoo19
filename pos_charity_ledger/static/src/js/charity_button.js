/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { CharityDonationPopup } from "@pos_charity_ledger/js/charity_popup";
import { useState } from "@odoo/owl";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosOrder.prototype, {
    serializeForORM(opts = {}) {
        const data = super.serializeForORM(opts);
        if (this._charity_donation_amount && this._charity_donation_amount > 0) {
            data.charity_donation_amount = this._charity_donation_amount;
            data.charity_account_id = this._charity_account_id || false;
        }
        return data;
    },
});

patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.charityState = useState({ donationAmount: 0, isDonating: false });
    },

    get charityEnabled() {
        return this.pos.config.charity_enabled && this.pos.config.charity_account_id;
    },

    get charityButtonLabel() {
        return this.pos.config.charity_button_label || "Donate to Charity";
    },

    get currencySymbol() {
        return this.pos.currency?.symbol || "₹";
    },

    async openCharityPopup() {
        if (!this.charityEnabled) return;

        const order = this.currentOrder;
        if (!order) return;

        // On the order screen, use the order total as the max donation cap,
        // or allow any positive amount (popup enforces max = order total).
        const orderTotal = order.get_total_with_tax ? order.get_total_with_tax() : (order.amount_total || 0);

        const result = await makeAwaitable(this.dialog, CharityDonationPopup, {
            title: this.charityButtonLabel,
            changeAmount: orderTotal > 0 ? orderTotal : 9999999,
            currencySymbol: this.currencySymbol,
        });

        if (result && result.confirmed && result.amount > 0) {
            this._applyCharityDonation(result.amount);
        }
    },

    _applyCharityDonation(amount) {
        const order = this.currentOrder;
        if (!order) return;
        const accountId = Array.isArray(this.pos.config.charity_account_id)
            ? this.pos.config.charity_account_id[0]
            : this.pos.config.charity_account_id;
        order._charity_donation_amount = amount;
        order._charity_account_id = accountId;
        this.charityState.donationAmount = amount;
        this.charityState.isDonating = true;
        this.notification.add(
            this.currencySymbol + amount.toFixed(2) + " will be donated to charity. Thank you!",
            { type: "success", sticky: false }
        );
    },

    removeCharityDonation() {
        const order = this.currentOrder;
        if (order) {
            order._charity_donation_amount = 0;
            order._charity_account_id = null;
        }
        this.charityState.donationAmount = 0;
        this.charityState.isDonating = false;
    },
});

///** @odoo-module **/
//
//import { patch } from "@web/core/utils/patch";
//import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
//import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
//import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
//import { CharityDonationPopup } from "@pos_charity_ledger/js/charity_popup";
//import { useState } from "@odoo/owl";
//import { PosOrder } from "@point_of_sale/app/models/pos_order";
//
//patch(PosOrder.prototype, {
//    serializeForORM(opts = {}) {
//        const data = super.serializeForORM(opts);
//        if (this._charity_donation_amount && this._charity_donation_amount > 0) {
//            data.charity_donation_amount = this._charity_donation_amount;
//            data.charity_account_id = this._charity_account_id || false;
//        }
//        return data;
//    },
//});
//
//patch(PaymentScreen.prototype, {
//    setup() {
//        super.setup(...arguments);
//        this.charityState = useState({ donationAmount: 0, isDonating: false });
//    },
//
//    get charityEnabled() {
//        return this.pos.config.charity_enabled && this.pos.config.charity_account_id;
//    },
//
//    get charityButtonLabel() {
//        return this.pos.config.charity_button_label || "Donate to Charity";
//    },
//
//    get changeAmount() {
//        const order = this.currentOrder;
//        if (!order) return 0;
//        const totalDue = order.totalDue || 0;
//        const totalPaid = (order.payment_ids || []).reduce((sum, line) => {
//            return sum + (line.getAmount ? line.getAmount() : (line.amount || 0));
//        }, 0);
//        const change = totalPaid - totalDue;
//        return change > 0 ? parseFloat(change.toFixed(2)) : 0;
//    },
//
//    get currencySymbol() {
//        return this.pos.currency?.symbol || "₹";
//    },
//
//    async openCharityPopup() {
//        if (!this.charityEnabled) return;
//        const changeAmt = this.changeAmount;
//        if (changeAmt <= 0) {
//            this.dialog.add(AlertDialog, {
//                title: "No Change Available",
//                body: "There is no change to donate. Please ensure the customer has overpaid.",
//            });
//            return;
//        }
//        const result = await makeAwaitable(this.dialog, CharityDonationPopup, {
//            title: this.charityButtonLabel,
//            changeAmount: changeAmt,
//            currencySymbol: this.currencySymbol,
//        });
//        if (result && result.confirmed && result.amount > 0) {
//            this._applyCharityDonation(result.amount);
//        }
//    },
//
//    _applyCharityDonation(amount) {
//        const order = this.currentOrder;
//        if (!order) return;
//        const accountId = Array.isArray(this.pos.config.charity_account_id)
//            ? this.pos.config.charity_account_id[0]
//            : this.pos.config.charity_account_id;
//        order._charity_donation_amount = amount;
//        order._charity_account_id = accountId;
//        this.charityState.donationAmount = amount;
//        this.charityState.isDonating = true;
//        this.notification.add(
//            this.currencySymbol + amount.toFixed(2) + " will be donated to charity. Thank you!",
//            { type: "success", sticky: false }
//        );
//    },
//
//    removeCharityDonation() {
//        const order = this.currentOrder;
//        if (order) {
//            order._charity_donation_amount = 0;
//            order._charity_account_id = null;
//        }
//        this.charityState.donationAmount = 0;
//        this.charityState.isDonating = false;
//    },
//
//    async validateOrder(isForceValidate) {
//        const result = await super.validateOrder(isForceValidate);
//        this.charityState.donationAmount = 0;
//        this.charityState.isDonating = false;
//        return result;
//    },
//});
