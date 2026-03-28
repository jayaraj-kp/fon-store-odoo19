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
// Odoo 19 CE: `get_total_with_tax` does NOT exist on PosOrder — do NOT patch it.
//
// APPROACH:
//   We do NOT inflate totalDue or isPaid on the order model because doing so
//   breaks the quick-pay buttons (Cash KDTY / Card KDTY) which auto-add a
//   payment line for `amount_total` — leading to an under-payment.
//
//   Instead we let the order model stay untouched and handle everything in
//   the PaymentScreen patch:
//     • When entering the payment screen, if a donation is pending we add
//       it to the existing payment line(s) so the correct amount is collected.
//     • serializeForORM sends charity data + corrects amount_return.
//     • For quick-pay (one-click from order screen), we intercept at the
//       ProductScreen / ControlButtons level by navigating to PaymentScreen
//       first, where the payment line adjustment can happen.
//
//   For the Python backend we correct amount_return so core doesn't see
//   the donated amount as change (see pos_order.py).
//
patch(PosOrder.prototype, {
    // Send charity data to Python backend.
    // Also correct amount_return: the donated ₹ is NOT change for the customer.
    serializeForORM(opts = {}) {
        const data = super.serializeForORM(opts);
        const extra = this._charity_donation_amount || 0;
        if (extra > 0) {
            data.charity_donation_amount = extra;
            data.charity_account_id = this._charity_account_id || false;
            // Reduce amount_return so Python doesn't treat donation as change.
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
            if (typeof line[k] === "number" && line[k] > 0) return sum + line[k];
        }
        return sum;
    }, 0);
}

function getRawOrderTotal(order) {
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
        order.lines || order.orderlines || [];
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

/**
 * Inflate existing payment lines to cover the charity donation amount.
 *
 * When the cashier clicks Cash KDTY / Card KDTY from the order screen,
 * Odoo auto-adds a payment line for `amount_total` (e.g. ₹397).
 * But we need ₹400 collected (₹397 product + ₹3 charity).
 *
 * This function finds the payment line and increases its amount by the
 * donation so the order becomes fully paid at the higher amount.
 *
 * Called from PaymentScreen.setup() (after payment lines are set)
 * and from validateOrder() before the core validation runs.
 */
function adjustPaymentLinesForCharity(order) {
    const extra = order._charity_donation_amount || 0;
    if (extra <= 0) return;

    const paymentLines = order.payment_ids || [];
    const arr = Array.isArray(paymentLines) ? paymentLines : [...paymentLines];
    if (arr.length === 0) return;

    // Add the donation to the first (or only) payment line.
    // This is the line that was auto-created by the quick-pay button.
    const line = arr[0];
    const currentAmount = typeof line.getAmount === "function"
        ? line.getAmount()
        : (line.amount || 0);

    const requiredTotal = (order.amount_total || 0) + extra;
    const currentTotal = arr.reduce((s, l) => {
        return s + (typeof l.getAmount === "function" ? l.getAmount() : (l.amount || 0));
    }, 0);

    const shortfall = parseFloat((requiredTotal - currentTotal).toFixed(2));
    if (shortfall <= 0) return; // Already fully covers the donation.

    // Set the line amount to cover the shortfall.
    const newAmount = parseFloat((currentAmount + shortfall).toFixed(2));
    if (typeof line.setAmount === "function") {
        line.setAmount(newAmount);
    } else {
        line.amount = newAmount;
    }
    _logger_debug(`[Charity] Adjusted payment line from ${currentAmount} to ${newAmount} (shortfall: ${shortfall})`);
}

function _logger_debug(msg) {
    // Safe console log wrapper
    try { console.debug(msg); } catch (_) {}
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

        // When the PaymentScreen mounts, payment lines already exist
        // (either from quick-pay or from the user clicking Payment button).
        // Adjust them immediately so the displayed amount is correct.
        const order = this.currentOrder;
        if (order && (order._charity_donation_amount || 0) > 0) {
            adjustPaymentLinesForCharity(order);
            this.charityState.donationAmount = order._charity_donation_amount;
            this.charityState.isDonating = true;
        }
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
        // Use the raw order total (not totalDue) to compute change —
        // the donation is not change for the customer.
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
        // Immediately adjust existing payment lines to cover the donation.
        adjustPaymentLinesForCharity(order);
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
            const extra = order._charity_donation_amount || 0;
            clearDonationFromOrder(order);
            // Undo the payment line adjustment.
            if (extra > 0) {
                const paymentLines = order.payment_ids || [];
                const arr = Array.isArray(paymentLines) ? paymentLines : [...paymentLines];
                if (arr.length > 0) {
                    const line = arr[0];
                    const currentAmount = typeof line.getAmount === "function"
                        ? line.getAmount() : (line.amount || 0);
                    const newAmount = Math.max(0, parseFloat((currentAmount - extra).toFixed(2)));
                    if (typeof line.setAmount === "function") {
                        line.setAmount(newAmount);
                    } else {
                        line.amount = newAmount;
                    }
                }
            }
        }
        this.charityState.donationAmount = 0;
        this.charityState.isDonating = false;
    },

    async validateOrder(isForceValidate) {
        const order = this.currentOrder;
        // Final safety net: ensure payment lines are adjusted before validation.
        if (order && (order._charity_donation_amount || 0) > 0) {
            adjustPaymentLinesForCharity(order);
        }
        const result = await super.validateOrder(isForceValidate);
        this.charityState.donationAmount = 0;
        this.charityState.isDonating = false;
        return result;
    },
});