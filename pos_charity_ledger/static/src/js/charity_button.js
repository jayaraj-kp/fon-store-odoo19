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

// ── Extend POS Order serialization ──────────────────────────────────────────
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

// ── Helpers ──────────────────────────────────────────────────────────────────
function getCurrencySymbol(pos) {
    return pos.currency?.symbol || "₹";
}

function computeRoundOff(total) {
    const ceil = Math.ceil(total);
    const diff = parseFloat((ceil - total).toFixed(2));
    return diff > 0 ? diff : 0;
}

/**
 * Scan an object for the first numeric value > 0 under any of the given keys.
 */
function pickFromObj(obj, keys) {
    if (!obj || typeof obj !== "object") return 0;
    for (const k of keys) {
        if (typeof obj[k] === "number" && obj[k] > 0) return obj[k];
    }
    return 0;
}

const TOTAL_KEYS = [
    "total_with_tax", "totalWithTax", "total_taxed", "taxed_total",
    "grand_total", "amount_total", "price_with_tax", "subtotal",
    "total",
];

/**
 * Get the order total for Odoo 19 CE.
 *
 * Odoo 19 stores prices in order._prices = { original: {...}, unit: {...} }
 * The grand total (inc. tax) lives at _prices.original.total_with_tax
 * or similar — we probe every likely key inside each sub-object.
 */
function getOrderTotal(order) {
    // ── Odoo 19: _prices.original / _prices.unit ─────────────────────────────
    if (order._prices && typeof order._prices === "object") {
        // Try nested sub-objects first (original > unit > top-level)
        for (const sub of ["original", "unit"]) {
            const v = pickFromObj(order._prices[sub], TOTAL_KEYS);
            if (v > 0) return v;
        }
        // Try top-level _prices keys
        const v = pickFromObj(order._prices, TOTAL_KEYS);
        if (v > 0) return v;

        // tax_amount + total inside any sub-object
        for (const sub of ["original", "unit"]) {
            const p = order._prices[sub];
            if (p && typeof p.tax_amount === "number" && typeof p.total === "number") {
                const v2 = p.tax_amount + p.total;
                if (v2 > 0) return v2;
            }
        }
    }

    // ── Odoo 16/17/18: method calls ──────────────────────────────────────────
    for (const m of ["get_total_with_tax", "getTotalWithTax", "getTotal", "get_total"]) {
        try {
            if (typeof order[m] === "function") {
                const v = order[m]();
                if (typeof v === "number" && v > 0) return v;
            }
        } catch (_) {}
    }

    // ── Direct properties ────────────────────────────────────────────────────
    const v2 = pickFromObj(order, TOTAL_KEYS);
    if (v2 > 0) return v2;

    // ── Last resort: sum order lines ─────────────────────────────────────────
    const lines =
        (typeof order.get_orderlines === "function" && order.get_orderlines()) ||
        order.lines ||
        order.orderlines ||
        [];
    const arr = Array.isArray(lines) ? lines : [...lines];
    return arr.reduce((s, l) => {
        const v =
            (typeof l.get_price_with_tax === "function" && l.get_price_with_tax()) ||
            l.price_subtotal_incl ||
            l.price_with_tax ||
            0;
        return s + (typeof v === "number" ? v : 0);
    }, 0);
}

function getCurrentOrder(pos) {
    try { const o = pos.get_order?.(); if (o) return o; } catch (_) {}
    try { const o = pos.getCurrentOrder?.(); if (o) return o; } catch (_) {}
    return pos.selectedOrder || null;
}

// ── Order Screen Charity Button Component ────────────────────────────────────
export class CharityOrderButton extends Component {
    static template = "pos_charity_ledger.CharityOrderButton";
    static props = {};

    setup() {
        try {
            this.pos = useService("pos");
        } catch (_) {
            this.pos = this.env.pos;
        }
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

    get orderRoundOffAmount() {
        const order = this.currentOrder;
        if (!order) return 0;
        return computeRoundOff(getOrderTotal(order));
    }

    async openOrderCharityPopup() {
        if (!this.charityEnabled) return;
        const order = this.currentOrder;
        if (!order) {
            this.notification.add("No active order found.", { type: "warning" });
            return;
        }

        const total = getOrderTotal(order);

        // Diagnostic — expand in console to find the right key
        console.log("[CharityButton] _prices.original:", JSON.parse(JSON.stringify(order._prices?.original || {})));
        console.log("[CharityButton] _prices.unit:", JSON.parse(JSON.stringify(order._prices?.unit || {})));
        console.log("[CharityButton] resolved total:", total);

        if (total <= 0) {
            this.notification.add("Please add products before donating.", { type: "warning" });
            return;
        }

        const roundOff = computeRoundOff(total);
        const maxDonate = roundOff > 0 ? roundOff : 1;

        const result = await makeAwaitable(this.dialog, CharityDonationPopup, {
            title: this.charityButtonLabel,
            changeAmount: maxDonate,
            roundOffAmount: roundOff,
            currencySymbol: this.currencySymbol,
        });

        if (result && result.confirmed && result.amount > 0) {
            const accountId = Array.isArray(this.pos.config.charity_account_id)
                ? this.pos.config.charity_account_id[0]
                : this.pos.config.charity_account_id;
            order._charity_donation_amount = result.amount;
            order._charity_account_id = accountId;
            this.charityState.donationAmount = result.amount;
            this.charityState.isDonating = true;
            this.notification.add(
                this.currencySymbol + result.amount.toFixed(2) + " will be donated to charity. Thank you!",
                { type: "success", sticky: false }
            );
        }
    }

    removeOrderCharityDonation() {
        const order = this.currentOrder;
        if (order) {
            order._charity_donation_amount = 0;
            order._charity_account_id = null;
        }
        this.charityState.donationAmount = 0;
        this.charityState.isDonating = false;
    }
}

// ── Patch PaymentScreen ───────────────────────────────────────────────────────
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