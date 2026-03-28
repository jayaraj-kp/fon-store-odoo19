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

// ═══════════════════════════════════════════════════════════════════════
// DESIGN — How charity works in Odoo 19 CE
// ═══════════════════════════════════════════════════════════════════════
//
// SCENARIO A – Donation from ORDER SCREEN (before payment):
//   Order total = ₹467, charity = ₹3
//   Cashier enters ₹467 cash → amount_paid=467, amount_return=0, total=467 ✓
//   We NEVER touch the payment line.
//   serializeForORM sends: charity_donation_amount=3, charity_account_id=X
//   Backend saves the donation on the order record.
//   At session close a journal entry moves ₹3 from cash GL → charity GL.
//
// SCENARIO B – Donation from PAYMENT SCREEN (customer overpaid):
//   Order total = ₹467, customer pays ₹470
//   amount_paid=470, amount_return=3 (Odoo computes automatically)
//   Cashier clicks "Donate ₹3" → charity = ₹3
//   We NEVER touch the payment line.
//   Backend: 470 - 3 = 467 ✓ — standard Odoo validation passes.
//
// KEY INSIGHT: We NEVER inflate/deflate payment lines.
// The ₹3 charity is stored only as charity_donation_amount on the order.
// Odoo's standard amount_paid / amount_return logic handles the rest.
// ═══════════════════════════════════════════════════════════════════════

// ── PosOrder patch ────────────────────────────────────────────────────────────
patch(PosOrder.prototype, {
    serializeForORM(opts = {}) {
        const data = super.serializeForORM(opts);
        const extra = this._charity_donation_amount || 0;
        if (extra > 0) {
            data.charity_donation_amount = extra;
            data.charity_account_id = this._charity_account_id || false;
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

function getRawOrderTotal(order) {
    for (const p of ["amount_total", "total_with_tax", "totalWithTax", "total"]) {
        const v = order[p];
        if (typeof v === "number" && v > 0) return v;
    }
    const lines =
        (typeof order.get_orderlines === "function" && order.get_orderlines()) ||
        order.lines || order.orderlines || [];
    const arr = Array.isArray(lines) ? lines : [...lines];
    return arr.reduce((s, l) => {
        const byM =
            (typeof l.get_price_with_tax === "function" && l.get_price_with_tax()) ||
            (typeof l.getPriceWithTax === "function" && l.getPriceWithTax());
        if (typeof byM === "number" && byM > 0) return s + byM;
        const byP = l.price_subtotal_incl || l.price_with_tax || 0;
        if (typeof byP === "number" && byP > 0) return s + byP;
        const pu = typeof l.price_unit === "number" ? l.price_unit : 0;
        const qty = typeof l.qty === "number" ? l.qty : (typeof l.quantity === "number" ? l.quantity : 1);
        const disc = typeof l.discount === "number" ? l.discount : 0;
        return s + pu * qty * (1 - disc / 100);
    }, 0);
}

function getPaymentLineAmount(line) {
    if (typeof line.getAmount === "function") {
        try { return line.getAmount(); } catch (_) {}
    }
    if (typeof line.get_amount === "function") {
        try { return line.get_amount(); } catch (_) {}
    }
    return typeof line.amount === "number" ? line.amount : 0;
}

function getPaymentLines(order) {
    const raw = order.payment_ids || order.paymentlines || [];
    return Array.isArray(raw) ? raw : [...raw];
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

// ── Order Screen Charity Button Component ─────────────────────────────────────
export class CharityOrderButton extends Component {
    static template = "pos_charity_ledger.CharityOrderButton";
    static props = {};

    setup() {
        try { this.pos = useService("pos"); } catch (_) { this.pos = this.env.pos; }
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
    get currencySymbol() { return getCurrencySymbol(this.pos); }
    get currentOrder() { return getCurrentOrder(this.pos); }

    get orderRoundOffAmount() {
        const order = this.currentOrder;
        return order ? computeRoundOff(getRawOrderTotal(order)) : 0;
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
        // No payment line exists yet on order screen → no cap.
        const maxDonate = roundOff > 0 ? roundOff : Infinity;
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
            this.charityState.isDonating = true;
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
        this.charityState.isDonating = false;
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
            // Restore badge if cashier navigated back to payment screen
            // after having set charity from the order screen.
            const order = this.currentOrder;
            if (order && (order._charity_donation_amount || 0) > 0) {
                this.charityState.donationAmount = order._charity_donation_amount;
                this.charityState.isDonating = true;
            }
        });
    },

    // ─────────────────────────────────────────────────────────────────
    // openCharityPopup — payment screen button (SCENARIO B only).
    // The customer has already overpaid. The change amount equals the
    // donation we record. No payment line changes are made.
    // ─────────────────────────────────────────────────────────────────
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
        this.charityState.donationAmount = amount;
        this.charityState.isDonating = true;
        this.notification.add(
            `${this.currencySymbol}${amount.toFixed(2)} will be donated to charity. Thank you!`,
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
        // No payment line manipulation needed.
        // serializeForORM (patched on PosOrder above) sends the charity fields
        // to the backend, which saves them via _process_order in pos_order.py.
        const result = await super.validateOrder(isForceValidate);
        this.charityState.donationAmount = 0;
        this.charityState.isDonating = false;
        return result;
    },
});

// ── Define getters OUTSIDE patch() ───────────────────────────────────────────
Object.defineProperties(PaymentScreen.prototype, {
    charityEnabled: {
        get() {
            return this.pos.config.charity_enabled && this.pos.config.charity_account_id;
        },
        configurable: true,
    },
    charityButtonLabel: {
        get() {
            return this.pos.config.charity_button_label || "Donate to Charity";
        },
        configurable: true,
    },
    currencySymbol: {
        get() { return getCurrencySymbol(this.pos); },
        configurable: true,
    },
    // changeAmount: how much the customer has overpaid right now.
    // Only used for Scenario B (payment screen donation button).
    changeAmount: {
        get() {
            const order = this.currentOrder;
            if (!order) return 0;
            const totalDue = order.amount_total || order.totalDue || 0;
            const totalPaid = getPaymentLines(order).reduce(
                (s, l) => s + getPaymentLineAmount(l), 0
            );
            const change = parseFloat((totalPaid - totalDue).toFixed(2));
            return change > 0 ? change : 0;
        },
        configurable: true,
    },
});