/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { CharityDonationPopup } from "@pos_charity_ledger/js/charity_popup";
import { useState } from "@odoo/owl";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

// ── Extend POS Order to carry charity data through serialization ─────────────
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

// ── Shared helpers (used by both screens) ────────────────────────────────────
function getCharityEnabled(pos) {
    return pos.config.charity_enabled && pos.config.charity_account_id;
}

function getCurrencySymbol(pos) {
    return pos.currency?.symbol || "₹";
}

/**
 * Compute the round-up amount for a given total.
 * e.g. 299  → 1  (next multiple of 1 above 299 … already integer, so 300-299=1)
 *      299.5 → 0.5
 *      300   → 0  (already a round number)
 */
function computeRoundOff(total) {
    const ceil = Math.ceil(total);
    const diff = parseFloat((ceil - total).toFixed(2));
    return diff > 0 ? diff : 0;
}

// ── Patch PaymentScreen ───────────────────────────────────────────────────────
patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.charityState = useState({ donationAmount: 0, isDonating: false });
    },

    get charityEnabled() {
        return getCharityEnabled(this.pos);
    },

    get charityButtonLabel() {
        return this.pos.config.charity_button_label || "Donate to Charity";
    },

    get changeAmount() {
        const order = this.currentOrder;
        if (!order) return 0;
        const totalDue = order.totalDue || 0;
        const totalPaid = (order.payment_ids || []).reduce((sum, line) => {
            return sum + (line.getAmount ? line.getAmount() : (line.amount || 0));
        }, 0);
        const change = totalPaid - totalDue;
        return change > 0 ? parseFloat(change.toFixed(2)) : 0;
    },

    get currencySymbol() {
        return getCurrencySymbol(this.pos);
    },

    async openCharityPopup() {
        if (!this.charityEnabled) return;
        const changeAmt = this.changeAmount;
        if (changeAmt <= 0) {
            this.dialog.add(AlertDialog, {
                title: "No Change Available",
                body: "There is no change to donate. Please ensure the customer has overpaid.",
            });
            return;
        }
        // Round-off is 0 on payment screen (change already known)
        const result = await makeAwaitable(this.dialog, CharityDonationPopup, {
            title: this.charityButtonLabel,
            changeAmount: changeAmt,
            roundOffAmount: 0,
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

    async validateOrder(isForceValidate) {
        const result = await super.validateOrder(isForceValidate);
        this.charityState.donationAmount = 0;
        this.charityState.isDonating = false;
        return result;
    },
});

// ── Patch ProductScreen ───────────────────────────────────────────────────────
patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.orderCharityState = useState({ donationAmount: 0, isDonating: false });
    },

    get charityEnabled() {
        return getCharityEnabled(this.pos);
    },

    get charityButtonLabel() {
        return this.pos.config.charity_button_label || "Donate to Charity";
    },

    get currencySymbol() {
        return getCurrencySymbol(this.pos);
    },

    /** Round-off amount for the current order total */
    get orderRoundOffAmount() {
        const order = this.currentOrder;
        if (!order) return 0;
        return computeRoundOff(order.getTotalWithTax ? order.getTotalWithTax() : (order.amount_total || 0));
    },

    async openOrderCharityPopup() {
        if (!this.charityEnabled) return;
        const order = this.currentOrder;
        if (!order || !(order.orderlines && order.orderlines.length)) {
            this.notification.add("Please add products before donating.", { type: "warning" });
            return;
        }

        const total = order.getTotalWithTax ? order.getTotalWithTax() : (order.amount_total || 0);
        if (total <= 0) {
            this.notification.add("No order total to calculate round-off.", { type: "warning" });
            return;
        }

        // Maximum donatable = round-off amount (the gap to next rupee)
        const roundOff = computeRoundOff(total);
        // If total is already a round number, allow up to 1 rupee as a goodwill donation
        const maxDonate = roundOff > 0 ? roundOff : 1;

        const result = await makeAwaitable(this.dialog, CharityDonationPopup, {
            title: this.charityButtonLabel,
            changeAmount: maxDonate,
            roundOffAmount: roundOff,
            currencySymbol: this.currencySymbol,
        });

        if (result && result.confirmed && result.amount > 0) {
            this._applyOrderCharityDonation(result.amount);
        }
    },

    _applyOrderCharityDonation(amount) {
        const order = this.currentOrder;
        if (!order) return;
        const accountId = Array.isArray(this.pos.config.charity_account_id)
            ? this.pos.config.charity_account_id[0]
            : this.pos.config.charity_account_id;
        order._charity_donation_amount = amount;
        order._charity_account_id = accountId;
        this.orderCharityState.donationAmount = amount;
        this.orderCharityState.isDonating = true;
        this.notification.add(
            this.currencySymbol + amount.toFixed(2) + " will be donated to charity. Thank you!",
            { type: "success", sticky: false }
        );
    },

    removeOrderCharityDonation() {
        const order = this.currentOrder;
        if (order) {
            order._charity_donation_amount = 0;
            order._charity_account_id = null;
        }
        this.orderCharityState.donationAmount = 0;
        this.orderCharityState.isDonating = false;
    },
});
