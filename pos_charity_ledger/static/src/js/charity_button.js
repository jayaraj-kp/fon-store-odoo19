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

// ── Extend POS Order ─────────────────────────────────────────────────────────
//
// KEY CHANGE: Override `totalDue` so that when a charity donation is set,
// the payment screen shows (and collects) the original total PLUS the donation.
//
// Example: product ₹296, donation ₹4 → totalDue becomes ₹300.
// The cashier collects ₹300; the ₹4 surplus is recorded as charity, not change.
//
patch(PosOrder.prototype, {
    // Odoo 19 CE exposes totalDue as a getter on PosOrder.
    // We wrap it to add the charity donation so the payment screen demands
    // the correct (rounded-up) amount from the customer.
    get totalDue() {
        const base = super.totalDue;
        const extra = this._charity_donation_amount || 0;
        return base + extra;
    },

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
    const ceil = Math.ceil(total / 10) * 10;
    const diff = parseFloat((ceil - total).toFixed(2));
    return diff > 0 ? diff : 0;
}

function sumBaseLines(baseLines) {
    if (!Array.isArray(baseLines) || baseLines.length === 0) return 0;
    return baseLines.reduce((sum, line) => {
        const priceUnit = typeof line.price_unit === "number" ? line.price_unit : 0;
        const qty = typeof line.quantity === "number" ? line.quantity : 1;
        const discount = typeof line.discount === "number" ? line.discount : 0;
        if (priceUnit > 0) {
            return sum + priceUnit * qty * (1 - discount / 100);
        }
        const fallbackKeys = [
            "priceSubtotalIncl", "price_subtotal_incl",
            "priceIncludingTax", "totalIncludingTax",
            "subtotal_incl", "priceSubtotal",
            "price_subtotal", "subtotal", "total", "amount",
        ];
        for (const k of fallbackKeys) {
            if (typeof line[k] === "number" && line[k] > 0) {
                return sum + line[k];
            }
        }
        return sum;
    }, 0);
}

function getOrderTotal(order) {
    for (const m of ["get_total_with_tax", "getTotalWithTax", "getTotal", "get_total"]) {
        try {
            if (typeof order[m] === "function") {
                const v = order[m]();
                if (typeof v === "number" && v > 0) return v;
            }
        } catch (_) {}
    }
    for (const p of ["amount_total", "total_with_tax", "totalWithTax", "total"]) {
        if (typeof order[p] === "number" && order[p] > 0) return order[p];
    }
    const original = order._prices?.original;
    if (original?.baseLines) {
        const v = sumBaseLines(original.baseLines);
        if (v > 0) return v;
    }
    const unit = order._prices?.unit;
    if (unit?.baseLines) {
        const v = sumBaseLines(unit.baseLines);
        if (v > 0) return v;
    }
    const lines =
        (typeof order.get_orderlines === "function" && order.get_orderlines()) ||
        order.lines ||
        order.orderlines ||
        [];
    const arr = Array.isArray(lines) ? lines : [...lines];
    if (arr.length > 0) {
        const lineTotal = arr.reduce((s, l) => {
            const byMethod =
                (typeof l.get_price_with_tax === "function" && l.get_price_with_tax()) ||
                (typeof l.getPriceWithTax === "function" && l.getPriceWithTax());
            if (typeof byMethod === "number" && byMethod > 0) return s + byMethod;
            const byProp = l.price_subtotal_incl || l.price_with_tax || 0;
            if (typeof byProp === "number" && byProp > 0) return s + byProp;
            const pu = typeof l.price_unit === "number" ? l.price_unit : 0;
            const qty = typeof l.qty === "number" ? l.qty : (typeof l.quantity === "number" ? l.quantity : 1);
            const disc = typeof l.discount === "number" ? l.discount : 0;
            return s + pu * qty * (1 - disc / 100);
        }, 0);
        if (lineTotal > 0) return lineTotal;
    }
    return 0;
}

function getCurrentOrder(pos) {
    try { const o = pos.get_order?.(); if (o) return o; } catch (_) {}
    try { const o = pos.getCurrentOrder?.(); if (o) return o; } catch (_) {}
    return pos.selectedOrder || null;
}

// ── Helper: apply donation to order ─────────────────────────────────────────
// Sets _charity_donation_amount and _charity_account_id on the order.
// Because totalDue is now patched to include the charity amount, the payment
// screen will automatically request the higher amount from the customer.
function applyDonationToOrder(pos, order, amount) {
    const accountId = Array.isArray(pos.config.charity_account_id)
        ? pos.config.charity_account_id[0]
        : pos.config.charity_account_id;
    order._charity_donation_amount = amount;
    order._charity_account_id = accountId;
}

function clearDonationFromOrder(order) {
    order._charity_donation_amount = 0;
    order._charity_account_id = null;
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

        if (total <= 0) {
            this.notification.add("Please add products before donating.", { type: "warning" });
            return;
        }

        const roundOff = computeRoundOff(total);
        const maxDonate = roundOff > 0 ? roundOff : Infinity;
        const ceilAmount = roundOff > 0 ? roundOff : 10;

        const result = await makeAwaitable(this.dialog, CharityDonationPopup, {
            title: this.charityButtonLabel,
            changeAmount: maxDonate,
            roundOffAmount: roundOff,
            ceilAmount: ceilAmount,
            currencySymbol: this.currencySymbol,
        });

        if (result && result.confirmed && result.amount > 0) {
            // Apply donation — totalDue on the order will automatically increase
            // by result.amount, so the payment screen shows the rounded-up total.
            applyDonationToOrder(this.pos, order, result.amount);
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
        if (order) clearDonationFromOrder(order);
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

    // changeAmount is now the overpayment ABOVE the (already-inflated) totalDue.
    // When the customer hasn't paid yet, this will typically be 0.
    // The donation is baked into totalDue, so the cashier just needs to collect
    // the displayed amount — no separate change calculation needed.
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
        // Apply donation — totalDue will increase by `amount` automatically via the patch.
        applyDonationToOrder(this.pos, order, amount);
        this.charityState.donationAmount = amount;
        this.charityState.isDonating = true;
        this.notification.add(
            this.currencySymbol + amount.toFixed(2) + " will be donated to charity. Thank you!",
            { type: "success", sticky: false }
        );
    },

    removeCharityDonation() {
        const order = this.currentOrder;
        if (order) clearDonationFromOrder(order);
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