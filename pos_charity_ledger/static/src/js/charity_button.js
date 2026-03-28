/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { CharityDonationPopup } from "@pos_charity_ledger/js/charity_popup";
import { useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { Component } from "@odoo/owl";

// ── PosOrder patch ────────────────────────────────────────────────────────────
patch(PosOrder.prototype, {
    serializeForORM(opts = {}) {
        const data = super.serializeForORM(opts);
        const extra = this._charity_donation_amount || 0;
        if (extra > 0) {
            data.charity_donation_amount = extra;
            data.charity_account_id = this._charity_account_id || false;
            // ── DO NOT touch amount_return ────────────────────────────────────
            // Odoo validates: amount_paid - amount_return == amount_total (exact)
            //   e.g. 970 - 6 = 964 ✓  (leave it as-is)
            // Zeroing amount_return → 970 - 0 = 970 ≠ 964 → "not fully paid" ✗
            // The ₹6 "change" physically goes into the charity box.
            // The charity journal entry at session close handles the accounting.
        }
        return data;
    },
});

// ── Helpers ───────────────────────────────────────────────────────────────────
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
        const qty      = typeof line.quantity  === "number" ? line.quantity  : 1;
        const discount = typeof line.discount  === "number" ? line.discount  : 0;
        if (priceUnit > 0) return sum + priceUnit * qty * (1 - discount / 100);
        const fallback = [
            "priceSubtotalIncl","price_subtotal_incl","priceIncludingTax",
            "totalIncludingTax","subtotal_incl","priceSubtotal",
            "price_subtotal","subtotal","total","amount",
        ];
        for (const k of fallback) {
            if (typeof line[k] === "number" && line[k] > 0) return sum + line[k];
        }
        return sum;
    }, 0);
}

function getRawOrderTotal(order) {
    for (const p of ["amount_total","total_with_tax","totalWithTax","total"]) {
        const v = order[p];
        if (typeof v === "number" && v > 0) return v;
    }
    const orig = order._prices?.original;
    if (orig?.baseLines) { const v = sumBaseLines(orig.baseLines); if (v > 0) return v; }
    const unit = order._prices?.unit;
    if (unit?.baseLines) { const v = sumBaseLines(unit.baseLines); if (v > 0) return v; }
    const lines =
        (typeof order.get_orderlines === "function" && order.get_orderlines()) ||
        order.lines || order.orderlines || [];
    const arr = Array.isArray(lines) ? lines : [...lines];
    return arr.reduce((s, l) => {
        const byM = (typeof l.get_price_with_tax === "function" && l.get_price_with_tax()) ||
                    (typeof l.getPriceWithTax    === "function" && l.getPriceWithTax());
        if (typeof byM === "number" && byM > 0) return s + byM;
        const byP = l.price_subtotal_incl || l.price_with_tax || 0;
        if (typeof byP === "number" && byP > 0) return s + byP;
        const pu   = typeof l.price_unit === "number" ? l.price_unit : 0;
        const qty  = typeof l.qty === "number" ? l.qty : (typeof l.quantity === "number" ? l.quantity : 1);
        const disc = typeof l.discount === "number" ? l.discount : 0;
        return s + pu * qty * (1 - disc / 100);
    }, 0);
}

function getCurrentOrder(pos) {
    try { const o = pos.get_order?.();       if (o) return o; } catch (_) {}
    try { const o = pos.getCurrentOrder?.(); if (o) return o; } catch (_) {}
    return pos.selectedOrder || null;
}

function applyDonationToOrder(pos, order, amount) {
    const accountId = Array.isArray(pos.config.charity_account_id)
        ? pos.config.charity_account_id[0]
        : pos.config.charity_account_id;
    order._charity_donation_amount = amount;
    order._charity_account_id     = accountId;
}

function clearDonationFromOrder(order) {
    order._charity_donation_amount = 0;
    order._charity_account_id     = null;
}

function setPaymentLineAmount(line, newAmount) {
    newAmount = parseFloat(newAmount.toFixed(2));
    if (typeof line.update === "function") {
        try { line.update({ amount: newAmount }); return; } catch (_) {}
    }
    if (typeof line.setAmount === "function") {
        try { line.setAmount(newAmount); return; } catch (_) {}
    }
    line.amount = newAmount;
}

function getPaymentLineAmount(line) {
    if (typeof line.getAmount === "function") {
        try { return line.getAmount(); } catch (_) {}
    }
    return typeof line.amount === "number" ? line.amount : 0;
}

// ── Order Screen Charity Button Component ─────────────────────────────────────
export class CharityOrderButton extends Component {
    static template = "pos_charity_ledger.CharityOrderButton";
    static props = {};

    setup() {
        try { this.pos = useService("pos"); } catch (_) { this.pos = this.env.pos; }
        this.dialog       = useService("dialog");
        this.notification = useService("notification");
        this.charityState = useState({ donationAmount: 0, isDonating: false });
    }

    get charityEnabled()    { return this.pos.config.charity_enabled && this.pos.config.charity_account_id; }
    get charityButtonLabel(){ return this.pos.config.charity_button_label || "Donate to Charity"; }
    get currencySymbol()    { return getCurrencySymbol(this.pos); }
    get currentOrder()      { return getCurrentOrder(this.pos); }

    get orderRoundOffAmount() {
        const order = this.currentOrder;
        return order ? computeRoundOff(getRawOrderTotal(order)) : 0;
    }

    async openOrderCharityPopup() {
        if (!this.charityEnabled) return;
        const order = this.currentOrder;
        if (!order) { this.notification.add("No active order found.", { type: "warning" }); return; }

        const total = getRawOrderTotal(order);
        if (total <= 0) { this.notification.add("Please add products before donating.", { type: "warning" }); return; }

        const roundOff   = computeRoundOff(total);
        const maxDonate  = roundOff > 0 ? roundOff : Infinity;
        const ceilAmount = roundOff > 0 ? roundOff : 10;

        const result = await makeAwaitable(this.dialog, CharityDonationPopup, {
            title: this.charityButtonLabel,
            changeAmount: maxDonate,
            roundOffAmount: roundOff,
            ceilAmount,
            currencySymbol: this.currencySymbol,
        });

        if (result?.confirmed && result.amount > 0) {
            applyDonationToOrder(this.pos, order, result.amount);
            this.charityState.donationAmount = result.amount;
            this.charityState.isDonating     = true;
            this.notification.add(
                `${this.currencySymbol}${result.amount.toFixed(2)} will be donated to charity. Thank you!`,
                { type: "success", sticky: false }
            );
        }
    }

    removeOrderCharityDonation() {
        const order = this.currentOrder;
        if (order) clearDonationFromOrder(order);
        this.charityState.donationAmount = 0;
        this.charityState.isDonating     = false;
    }
}

// ── Patch PaymentScreen ───────────────────────────────────────────────────────
// NOTE: getter syntax (get foo() {}) inside patch() causes a SyntaxError in
// Odoo 19's esbuild bundler. All getters are defined via Object.defineProperties
// AFTER the patch() call below.
patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.charityState = useState({ donationAmount: 0, isDonating: false });

        onMounted(() => {
            const order = this.currentOrder;
            if (order && (order._charity_donation_amount || 0) > 0) {
                this._inflatePaymentLines(order);
                this.charityState.donationAmount = order._charity_donation_amount;
                this.charityState.isDonating     = true;
            }
        });
    },

    // ── Inflate payment line so it covers order total + charity ──────────────
    // Used when cashier sets charity from the ORDER SCREEN before payment.
    // Example: order = ₹964, charity = ₹6 → inflate payment line from ₹964 → ₹970
    //          so that: amount_paid=970, amount_return=6, amount_total=964  ✓
    // When cashier already entered ₹970 on the payment screen the shortfall
    // is 0 and nothing changes (safe no-op).
    _inflatePaymentLines(order) {
        const extra = order._charity_donation_amount || 0;
        if (extra <= 0) return;

        const rawTotal = getRawOrderTotal(order);
        const required = parseFloat((rawTotal + extra).toFixed(2));

        const lines = order.payment_ids || [];
        const arr   = Array.isArray(lines) ? lines : [...lines];
        if (arr.length === 0) return;

        const currentPaid = arr.reduce((s, l) => s + getPaymentLineAmount(l), 0);
        const shortfall   = parseFloat((required - currentPaid).toFixed(2));
        if (shortfall <= 0.001) return;

        const line      = arr[0];
        const curAmount = getPaymentLineAmount(line);
        setPaymentLineAmount(line, curAmount + shortfall);

        console.debug(`[Charity] Payment line adjusted +${shortfall} → total ${curAmount + shortfall}`);
    },

    _deflatePaymentLines(order, extra) {
        if (extra <= 0) return;
        const lines = order.payment_ids || [];
        const arr   = Array.isArray(lines) ? lines : [...lines];
        if (arr.length === 0) return;

        const line      = arr[0];
        const curAmount = getPaymentLineAmount(line);
        const newAmount = Math.max(0, parseFloat((curAmount - extra).toFixed(2)));
        setPaymentLineAmount(line, newAmount);

        console.debug(`[Charity] Payment line deflated -${extra} → total ${newAmount}`);
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
        if (result?.confirmed && result.amount > 0) {
            this._applyCharityDonation(result.amount);
        }
    },

    _applyCharityDonation(amount) {
        const order = this.currentOrder;
        if (!order) return;
        applyDonationToOrder(this.pos, order, amount);
        // No payment line inflation needed: customer already overpaid by this
        // amount (changeAmount == amount), so payment line is already correct.
        this.charityState.donationAmount = amount;
        this.charityState.isDonating     = true;
        this.notification.add(
            `${this.currencySymbol}${amount.toFixed(2)} will be donated to charity. Thank you!`,
            { type: "success", sticky: false }
        );
    },

    removeCharityDonation() {
        const order = this.currentOrder;
        if (order) {
            const extra = order._charity_donation_amount || 0;
            clearDonationFromOrder(order);
            this._deflatePaymentLines(order, extra);
        }
        this.charityState.donationAmount = 0;
        this.charityState.isDonating     = false;
    },

    async validateOrder(isForceValidate) {
        const order = this.currentOrder;
        if (order && (order._charity_donation_amount || 0) > 0) {
            // Inflate only if charity was set from order screen (shortfall > 0).
            // On the payment screen the change already covers the donation → no-op.
            this._inflatePaymentLines(order);
        }
        const result = await super.validateOrder(isForceValidate);
        this.charityState.donationAmount = 0;
        this.charityState.isDonating     = false;
        return result;
    },
});

// ── Define getters OUTSIDE patch() ───────────────────────────────────────────
// Getter shorthand inside patch({}) triggers "Unexpected token 'get'" in
// Odoo 19's esbuild bundler. Object.defineProperties avoids the issue entirely.
Object.defineProperties(PaymentScreen.prototype, {
    charityEnabled: {
        get() { return this.pos.config.charity_enabled && this.pos.config.charity_account_id; },
        configurable: true,
    },
    charityButtonLabel: {
        get() { return this.pos.config.charity_button_label || "Donate to Charity"; },
        configurable: true,
    },
    currencySymbol: {
        get() { return getCurrencySymbol(this.pos); },
        configurable: true,
    },
    changeAmount: {
        get() {
            const order = this.currentOrder;
            if (!order) return 0;
            const totalDue  = order.totalDue || 0;
            const totalPaid = (order.payment_ids || []).reduce(
                (s, l) => s + getPaymentLineAmount(l), 0
            );
            const change = totalPaid - totalDue;
            return change > 0 ? parseFloat(change.toFixed(2)) : 0;
        },
        configurable: true,
    },
});