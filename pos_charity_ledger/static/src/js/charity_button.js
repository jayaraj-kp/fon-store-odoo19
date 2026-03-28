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
// Odoo 19 CE: `get_total_with_tax` is NOT a method — it does not exist on
// PosOrder. The order total is accessed via `order.amount_total` (reactive
// computed property) or `order.getTotalWithTax()` (may not exist either).
//
// The only safe getter to patch for the payment screen is `totalDue`.
// For the "is fully paid" check we patch `isPaid` directly, which is the
// actual gate that controls whether Validate is allowed.
//
// For the Python backend we send a corrected `amount_return` so the core
// "not fully paid" check passes (see pos_order.py).
//
patch(PosOrder.prototype, {
    // ── Inflate totalDue so payment screen shows & collects (total + donation) ─
    get totalDue() {
        const base = super.totalDue;
        const extra = this._charity_donation_amount || 0;
        return base + extra;
    },

    // ── isPaid: order is paid when payment covers (amount_total + donation) ──
    // Odoo 19 CE: isPaid() checks getTotalPaid() >= amount_total (with rounding).
    // We override so the inflated payment (₹300) satisfies the check for a
    // ₹296 order with ₹4 charity.
    isPaid() {
        const extra = this._charity_donation_amount || 0;
        if (extra <= 0) return super.isPaid(...arguments);

        // Total the customer must pay = product total + donation.
        const required = (this.amount_total || 0) + extra;

        // Sum all payment lines.
        const paid = (this.payment_ids || []).reduce((sum, line) => {
            return sum + (typeof line.getAmount === "function" ? line.getAmount() : (line.amount || 0));
        }, 0);

        // Use Odoo's currency rounding precision (2 decimal places).
        return Math.round((paid - required) * 100) >= 0;
    },

    // ── Serialize: send charity data + corrected amount_return to Python ─────
    serializeForORM(opts = {}) {
        const data = super.serializeForORM(opts);
        const extra = this._charity_donation_amount || 0;
        if (extra > 0) {
            data.charity_donation_amount = extra;
            data.charity_account_id = this._charity_account_id || false;

            // The cashier paid (amount_total + extra), e.g. ₹300 for ₹296 + ₹4.
            // Odoo core computes amount_return = amount_paid - amount_total = ₹4.
            // But ₹4 is NOT change — it's the donation. Reduce amount_return by
            // the donation so core gets 0 change and the "fully paid" check passes.
            if (typeof data.amount_return === "number" && data.amount_return > 0) {
                data.amount_return = Math.max(
                    0,
                    parseFloat((data.amount_return - extra).toFixed(2))
                );
            }
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

function getRawOrderTotal(order) {
    // Returns the product-only total (without any charity inflation).
    // Used for round-off hint on the order screen button.
    for (const p of ["amount_total", "total_with_tax", "totalWithTax", "total"]) {
        const v = order[p];
        if (typeof v === "number" && v > 0) return v;
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
            const qty = typeof l.qty === "number" ? l.qty :
                (typeof l.quantity === "number" ? l.quantity : 1);
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
        return computeRoundOff(getRawOrderTotal(order));
    }

    async openOrderCharityPopup() {
        if (!this.charityEnabled) return;
        const order = this.currentOrder;
        if (!order) {
            this.notification.add("No active order found.", { type: "warning" });
            return;
        }

        const total = getRawOrderTotal(order);

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