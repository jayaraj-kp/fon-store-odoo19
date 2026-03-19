/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { CharityDonationPopup } from "@pos_charity_ledger/js/charity_popup";
import { useState } from "@odoo/owl";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.charityState = useState({
            donationAmount: 0,
            isDonating: false,
        });
    },

    get charityEnabled() {
        return this.pos.config.charity_enabled && this.pos.config.charity_account_id;
    },

    get charityButtonLabel() {
        return this.pos.config.charity_button_label || "Donate to Charity";
    },

    get changeAmount() {
        const order = this.pos.get_order();
        if (!order) return 0;
        const totalPaid = order.get_total_paid();
        const totalDue = order.get_total_with_tax();
        const change = totalPaid - totalDue;
        return change > 0 ? parseFloat(change.toFixed(2)) : 0;
    },

    get currencySymbol() {
        return this.pos.currency?.symbol || "₹";
    },

    async openCharityPopup() {
        if (!this.charityEnabled) return;
        const changeAmt = this.changeAmount;
        if (changeAmt <= 0) {
            this.dialog.add(
                (await import("@web/core/confirmation_dialog/confirmation_dialog")).AlertDialog,
                {
                    title: "No Change Available",
                    body: "There is no change to donate. The customer has not overpaid.",
                }
            );
            return;
        }

        const result = await makeAwaitable(this.dialog, CharityDonationPopup, {
            title: this.charityButtonLabel,
            changeAmount: changeAmt,
            currencySymbol: this.currencySymbol,
        });

        if (result && result.confirmed && result.amount > 0) {
            this._applyCharityDonation(result.amount);
        }
    },

    _applyCharityDonation(amount) {
        const order = this.pos.get_order();
        if (!order) return;
        order.charity_donation_amount = amount;
        order.charity_account_id = Array.isArray(this.pos.config.charity_account_id)
            ? this.pos.config.charity_account_id[0]
            : this.pos.config.charity_account_id;
        this.charityState.donationAmount = amount;
        this.charityState.isDonating = true;

        this.notification.add(
            `${this.currencySymbol}${amount.toFixed(2)} will be donated to charity. Thank you!`,
            { type: "success", sticky: false }
        );
    },

    removeCharityDonation() {
        const order = this.pos.get_order();
        if (order) {
            order.charity_donation_amount = 0;
            order.charity_account_id = null;
        }
        this.charityState.donationAmount = 0;
        this.charityState.isDonating = false;
    },

    async validateOrder(isForceValidate) {
        const order = this.pos.get_order();
        if (order && this.charityState.isDonating && this.charityState.donationAmount > 0) {
            order.charity_donation_amount = this.charityState.donationAmount;
            order.charity_account_id = Array.isArray(this.pos.config.charity_account_id)
                ? this.pos.config.charity_account_id[0]
                : this.pos.config.charity_account_id;
        }
        return super.validateOrder(isForceValidate);
    },
});
