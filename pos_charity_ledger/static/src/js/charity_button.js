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
 * Sum baseLines array from Odoo 19's _prices structure.
 * Each baseLine object contains per-line tax computation data.
 * We try every plausible key for the tax-inclusive subtotal.
 */
function sumBaseLines(baseLines) {
    if (!Array.isArray(baseLines) || baseLines.length === 0) return 0;
    return baseLines.reduce((sum, line) => {
        // Try keys in order of likelihood for tax-inclusive total per line
        const keys = [
            "priceSubtotalIncl",
            "price_subtotal_incl",
            "priceIncludingTax",
            "totalIncludingTax",
            "subtotal_incl",
            "amountTax",      // may be just tax
            "priceSubtotal",  // excl. tax fallback
            "price_subtotal",
            "subtotal",
            "total",
            "amount",
        ];
        for (const k of keys) {
            if (typeof line[k] === "number" && line[k] > 0) {
                return sum + line[k];
            }
        }
        // If line has rawLine or line ref, skip — not a total holder
        return sum;
    }, 0);
}

/**
 * Get the order total for Odoo 19 CE.
 *
 * Odoo 19 _prices structure:
 *   order._prices = {
 *     original: { taxDetails: {}, baseLines: [{...}, ...], baseLineByLineUuids: {} },
 *     unit:     { taxDetails: {}, baseLines: [{...}, ...], baseLineByLineUuids: {} },
 *   }
 *
 * The grand total lives as the sum of baseLines inside _prices.original.
 */
function getOrderTotal(order) {
    // ── Odoo 19: sum _prices.original.baseLines ──────────────────────────────
    const original = order._prices?.original;
    if (original?.baseLines) {
        const v = sumBaseLines(original.baseLines);
        if (v > 0) return v;
    }

    // ── Odoo 19 fallback: _prices.unit.baseLines ─────────────────────────────
    const unit = order._prices?.unit;
    if (unit?.baseLines) {
        const v = sumBaseLines(unit.baseLines);
        if (v > 0) return v;
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

    // ── Direct property fallback ─────────────────────────────────────────────
    for (const p of ["amount_total", "total_with_tax", "total"]) {
        if (typeof order[p] === "number" && order[p] > 0) return order[p];
    }

    // ── Last resort: sum order lines directly ────────────────────────────────
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

        // Diagnostic: expand baseLines[0] in console to confirm key names
        const bl = order._prices?.original?.baseLines || [];
        console.log("[CharityButton] baseLines[0]:", bl[0] ? JSON.parse(JSON.stringify(bl[0])) : "empty");
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