/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { CharityDonationPopup } from "@pos_charity_ledger/js/charity_popup";
import { useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { Component } from "@odoo/owl";

/* =========================================================
   ✅ PATCH POS ORDER (ODOO 19 SAFE)
========================================================= */

patch(PosOrder.prototype, {
    serializeForORM(opts = {}) {
        const data = super.serializeForORM(opts);
        if (this._charity_donation_amount && this._charity_donation_amount > 0) {
            data.charity_donation_amount = this._charity_donation_amount;
            data.charity_account_id = this._charity_account_id || false;
        }
        return data;
    },

    // ✅ Add donation into total (SAFE METHOD)
    get_total_with_tax() {
        const baseTotal = super.get_total_with_tax(...arguments);
        return baseTotal + (this._charity_donation_amount || 0);
    },

    // ✅ IMPORTANT: Force UI refresh
    set_charity_amount(amount, accountId) {
        this._charity_donation_amount = amount;
        this._charity_account_id = accountId;

        // 🔥 Required for Odoo 19 reactive UI
        if (this._recomputePrices) {
            this._recomputePrices();
        } else if (this.trigger) {
            this.trigger("change");
        }
    },
});

/* =========================================================
   Helpers
========================================================= */

function getCurrencySymbol(pos) {
    return pos.currency?.symbol || "₹";
}

function getCurrentOrder(pos) {
    try { return pos.get_order?.(); } catch (_) {}
    try { return pos.getCurrentOrder?.(); } catch (_) {}
    return pos.selectedOrder || null;
}

/* =========================================================
   ORDER SCREEN BUTTON
========================================================= */

export class CharityOrderButton extends Component {
    static template = "pos_charity_ledger.CharityOrderButton";

    setup() {
        this.pos = useService("pos");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.charityState = useState({ donationAmount: 0, isDonating: false });
    }

    get charityEnabled() {
        return this.pos.config.charity_enabled && this.pos.config.charity_account_id;
    }

    get charityButtonLabel() {
        return this.pos.config.charity_button_label || "Donate to Charity";
    }

    get currencySymbol() {
        return getCurrencySymbol(this.pos);
    }

    get currentOrder() {
        return getCurrentOrder(this.pos);
    }

    async openOrderCharityPopup() {
        if (!this.charityEnabled) return;

        const order = this.currentOrder;
        if (!order) return;

        const result = await makeAwaitable(this.dialog, CharityDonationPopup, {
            title: this.charityButtonLabel,
            currencySymbol: this.currencySymbol,
        });

        if (result && result.confirmed && result.amount > 0) {
            const accountId = Array.isArray(this.pos.config.charity_account_id)
                ? this.pos.config.charity_account_id[0]
                : this.pos.config.charity_account_id;

            order.set_charity_amount(result.amount, accountId);

            this.charityState.donationAmount = result.amount;
            this.charityState.isDonating = true;

            this.notification.add(
                `${this.currencySymbol}${result.amount.toFixed(2)} added to total as charity.`,
                { type: "success" }
            );
        }
    }

    removeOrderCharityDonation() {
        const order = this.currentOrder;
        if (order) {
            order.set_charity_amount(0, null);
        }

        this.charityState.donationAmount = 0;
        this.charityState.isDonating = false;
    }
}

/* =========================================================
   PAYMENT SCREEN PATCH
========================================================= */

patch(PaymentScreen.prototype, {
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
        return getCurrencySymbol(this.pos);
    },

    async openCharityPopup() {
        if (!this.charityEnabled) return;

        const result = await makeAwaitable(this.dialog, CharityDonationPopup, {
            title: this.charityButtonLabel,
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

        order.set_charity_amount(amount, accountId);

        this.charityState.donationAmount = amount;
        this.charityState.isDonating = true;

        this.notification.add(
            `${this.currencySymbol}${amount.toFixed(2)} added to total as charity.`,
            { type: "success" }
        );
    },

    removeCharityDonation() {
        const order = this.currentOrder;
        if (order) {
            order.set_charity_amount(0, null);
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