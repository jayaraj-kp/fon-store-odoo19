/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

/**
 * Patch the PaymentScreen to add charity donation tracking.
 * The actual button is rendered via the XML template patch.
 */
patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.charityState = useState({
            donationAmount: 0,
            isDonating: false,
        });
    },

    /**
     * Returns whether the charity feature is enabled for this POS.
     */
    get charityEnabled() {
        return this.pos.config.charity_enabled && this.pos.config.charity_account_id;
    },

    /**
     * Label for the charity button from config.
     */
    get charityButtonLabel() {
        return this.pos.config.charity_button_label || "Donate to Charity";
    },

    /**
     * The change amount available for donation.
     */
    get changeAmount() {
        const order = this.pos.get_order();
        if (!order) return 0;
        const totalPaid = order.get_total_paid();
        const totalDue = order.get_total_with_tax();
        const change = totalPaid - totalDue;
        return change > 0 ? change : 0;
    },

    /**
     * Opens the charity popup.
     */
    async openCharityPopup() {
        if (!this.charityEnabled) return;

        const changeAmt = this.changeAmount;
        if (changeAmt <= 0) {
            await this.popup.add("ErrorPopup", {
                title: "No Change Available",
                body: "There is no change to donate. The customer hasn't overpaid.",
            });
            return;
        }

        const { confirmed, payload } = await this.popup.add("CharityDonationPopup", {
            title: this.charityButtonLabel,
            changeAmount: changeAmt,
            currency: this.pos.currency,
        });

        if (confirmed && payload && payload.amount > 0) {
            this._applyCharityDonation(payload.amount);
        }
    },

    /**
     * Apply the charity donation to the current order.
     */
    _applyCharityDonation(amount) {
        const order = this.pos.get_order();
        if (!order) return;

        // Store donation info on the order for backend processing
        order.charity_donation_amount = amount;
        order.charity_account_id = this.pos.config.charity_account_id[0];

        this.charityState.donationAmount = amount;
        this.charityState.isDonating = true;

        // Show confirmation
        this.notification.add(
            `₹${amount.toFixed(2)} will be donated to charity. Thank you!`,
            { type: "success", sticky: false }
        );
    },

    /**
     * Remove/cancel the charity donation.
     */
    removeCharityDonation() {
        const order = this.pos.get_order();
        if (order) {
            order.charity_donation_amount = 0;
            order.charity_account_id = null;
        }
        this.charityState.donationAmount = 0;
        this.charityState.isDonating = false;
    },

    /**
     * Override validate to include charity data in order.
     */
    async validateOrder(isForceValidate) {
        const order = this.pos.get_order();
        // Attach charity donation data to order JSON before sending
        if (order && this.charityState.isDonating && this.charityState.donationAmount > 0) {
            order.charity_donation_amount = this.charityState.donationAmount;
            order.charity_account_id = this.pos.config.charity_account_id?.[0];
        }
        return super.validateOrder(isForceValidate);
    },
});
