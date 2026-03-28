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

// ═══════════════════════════════════════════════════════════════════════════
// HOW IT WORKS — Odoo 19 CE
// ═══════════════════════════════════════════════════════════════════════════
//
// SCENARIO A — Charity set from ORDER SCREEN (before tapping a payment method)
//   Order = ₹297, charity = ₹3
//   → getDue() / get_due() returns ₹300 (patched below)
//   → Cashier taps "Cash KDTY" → Odoo auto-fills line = ₹300
//   → Payment screen shows: Cash ₹300, Change ₹3  ✓
//   → ₹3 "change" physically goes into the charity box
//   → amount_paid=300, amount_return=3, amount_total=297  ✓
//
// SCENARIO B — Charity set from PAYMENT SCREEN (customer already overpaid)
//   Order = ₹297, cashier enters ₹300 → change = ₹3
//   → Cashier clicks "Donate ₹3" → charity recorded, nothing else changes
//   → amount_paid=300, amount_return=3  ✓
//
// The key is patching BOTH getDue() and get_due() because Odoo 19 CE
// uses getDue() internally but some paths still call get_due().
// ═══════════════════════════════════════════════════════════════════════════

// ── PosOrder patches ──────────────────────────────────────────────────────────
patch(PosOrder.prototype, {

    /**
     * Odoo 19 CE calls getDue() to know how much the customer still owes.
     * By adding the charity amount here, when the cashier taps "Cash KDTY"
     * the payment line auto-fills to ₹300 instead of ₹297.
     * The ₹3 difference shows as "Change" — which goes into the charity box.
     */
    getDue(paymentLine) {
        const base = super.getDue(paymentLine);
        // Only add charity to the total-due (no paymentLine arg),
        // not to the per-line calculation (paymentLine arg present).
        if (!paymentLine) {
            return base + (this._charity_donation_amount || 0);
        }
        return base;
    },

    /**
     * Older code paths in Odoo 19 CE may still call get_due().
     * Mirror the patch here for safety.
     */
    get_due(paymentLine) {
        if (typeof super.get_due === "function") {
            const base = super.get_due(paymentLine);
            if (!paymentLine) {
                return base + (this._charity_donation_amount || 0);
            }
            return base;
        }
        // Fallback: compute manually
        const charity = !paymentLine ? (this._charity_donation_amount || 0) : 0;
        const total = this.amount_total || 0;
        const paid = (this.payment_ids || []).reduce((s, l) => {
            if (l === paymentLine) return s;
            return s + (typeof l.amount === "number" ? l.amount : 0);
        }, 0);
        return total - paid + charity;
    },

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
        const qty =
            typeof l.qty === "number" ? l.qty :
            typeof l.quantity === "number" ? l.quantity : 1;
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
        // No payment yet on order screen → no hard cap on donation amount.
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
            // after setting charity from the order screen.
            const order = this.currentOrder;
            if (order && (order._charity_donation_amount || 0) > 0) {
                this.charityState.donationAmount = order._charity_donation_amount;
                this.charityState.isDonating = true;
            }
        });
    },

    // ── Payment screen "Donate Change" button (SCENARIO B only) ──────────────
    // Shown when the customer has already overpaid.
    // Example: total=₹297, customer paid ₹300 → change=₹3 → donate ₹3.
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
        // Customer already paid ₹300 for ₹297 order — payment line is correct.
        // No line changes needed.
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
        // getDue() / get_due() is already patched to include charity.
        // Odoo's standard validation handles amount_paid / amount_return normally.
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
    // changeAmount: how much the customer has overpaid RIGHT NOW.
    // Measured against raw order total (not getDue) so it correctly reflects
    // real overpayment even when getDue() includes charity.
    changeAmount: {
        get() {
            const order = this.currentOrder;
            if (!order) return 0;
            const totalDue = getRawOrderTotal(order) || order.amount_total || 0;
            const totalPaid = getPaymentLines(order).reduce(
                (s, l) => s + getPaymentLineAmount(l), 0
            );
            const change = parseFloat((totalPaid - totalDue).toFixed(2));
            return change > 0 ? change : 0;
        },
        configurable: true,
    },
});