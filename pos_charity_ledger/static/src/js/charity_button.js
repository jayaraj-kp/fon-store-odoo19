/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { reactive } from "@odoo/owl";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { CharityDonationPopup } from "@pos_charity_ledger/js/charity_popup";
import { useState, onMounted, Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

// ═══════════════════════════════════════════════════════════════════════════
// MODULE-LEVEL REACTIVE STORE
// ═══════════════════════════════════════════════════════════════════════════
// OWL reactive() creates a proxy that automatically notifies EVERY component
// that reads from it whenever any key changes.
//
// We key by order.uid (stable per session).  When charityStore[uid] is set,
// Odoo's own PaymentScreen template (which reads getDue() → charityStore)
// re-renders automatically and the big ₹297 display becomes ₹300.
// ═══════════════════════════════════════════════════════════════════════════
const charityStore = reactive({});

function _orderKey(order) {
    return String(order.uid || order.id || order.name || "unknown");
}

function getCharityData(order) {
    return charityStore[_orderKey(order)] || { amount: 0, accountId: null };
}

function setCharityData(order, amount, accountId) {
    // Writing a key on the reactive object triggers re-render in all
    // components that have read this key (payment screen, order screen badge).
    charityStore[_orderKey(order)] = { amount, accountId };
}

function clearCharityData(order) {
    charityStore[_orderKey(order)] = { amount: 0, accountId: null };
}

// ── Helpers ────────────────────────────────────────────────────────────────
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

function getConfigAccountId(pos) {
    return Array.isArray(pos.config.charity_account_id)
        ? pos.config.charity_account_id[0]
        : pos.config.charity_account_id;
}

// ═══════════════════════════════════════════════════════════════════════════
// PosOrder patch
// getDue() reads from charityStore so the reactive dependency is registered.
// When charityStore changes → all components that called getDue() re-render.
// ═══════════════════════════════════════════════════════════════════════════
patch(PosOrder.prototype, {
    getDue(paymentLine) {
        const base = super.getDue(paymentLine);
        if (!paymentLine) {
            // Reading charityStore here registers the reactive dependency.
            return base + (getCharityData(this).amount || 0);
        }
        return base;
    },

    get_due(paymentLine) {
        if (typeof super.get_due === "function") {
            const base = super.get_due(paymentLine);
            if (!paymentLine) {
                return base + (getCharityData(this).amount || 0);
            }
            return base;
        }
        const charity = !paymentLine ? (getCharityData(this).amount || 0) : 0;
        const total = this.amount_total || 0;
        const paid = (this.payment_ids || []).reduce((s, l) => {
            if (l === paymentLine) return s;
            return s + (typeof l.amount === "number" ? l.amount : 0);
        }, 0);
        return total - paid + charity;
    },

    serializeForORM(opts = {}) {
        const data = super.serializeForORM(opts);
        const { amount, accountId } = getCharityData(this);
        if (amount > 0) {
            data.charity_donation_amount = amount;
            data.charity_account_id = accountId || false;
        }
        return data;
    },
});

// ═══════════════════════════════════════════════════════════════════════════
// Order Screen Charity Button Component
// ═══════════════════════════════════════════════════════════════════════════
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
    get currentOrder()   { return getCurrentOrder(this.pos); }

    get orderRawTotal() {
        const o = this.currentOrder;
        return o ? getRawOrderTotal(o) : 0;
    }
    get orderRoundOffAmount() {
        return computeRoundOff(this.orderRawTotal);
    }

    /** Called from XML template to compute displayed total */
    getRawOrderTotal(order) {
        return order ? getRawOrderTotal(order) : 0;
    }

    // ── ONE-TAP: instantly donate the round-off, no popup ─────────────────
    quickDonateRoundOff() {
        if (!this.charityEnabled) return;
        const order = this.currentOrder;
        if (!order) return;
        const roundOff = this.orderRoundOffAmount;
        if (roundOff <= 0) return;

        setCharityData(order, roundOff, getConfigAccountId(this.pos));
        this.charityState.donationAmount = roundOff;
        this.charityState.isDonating = true;

        const sym = this.currencySymbol;
        this.notification.add(
            `❤ ${sym}${roundOff.toFixed(2)} donated — Total: ${sym}${(this.orderRawTotal + roundOff).toFixed(2)}`,
            { type: "success", sticky: false }
        );
    }

    // ── POPUP flow: for whole-number totals or custom amounts ──────────────
    async openOrderCharityPopup() {
        if (!this.charityEnabled) return;
        const order = this.currentOrder;
        if (!order) {
            this.notification.add("No active order found.", { type: "warning" });
            return;
        }
        const total = this.orderRawTotal;
        if (total <= 0) {
            this.notification.add("Please add products before donating.", { type: "warning" });
            return;
        }
        const roundOff  = computeRoundOff(total);
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
            setCharityData(order, result.amount, getConfigAccountId(this.pos));
            this.charityState.donationAmount = result.amount;
            this.charityState.isDonating = true;
            const sym = this.currencySymbol;
            this.notification.add(
                `❤ ${sym}${result.amount.toFixed(2)} will be donated — Total: ${sym}${(total + result.amount).toFixed(2)}`,
                { type: "success", sticky: false }
            );
        }
    }

    removeOrderCharityDonation() {
        const order = this.currentOrder;
        if (order) clearCharityData(order);
        this.charityState.donationAmount = 0;
        this.charityState.isDonating = false;
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// PaymentScreen patch
// ═══════════════════════════════════════════════════════════════════════════
patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.charityState = useState({ donationAmount: 0, isDonating: false });

        onMounted(() => {
            // Restore badge if cashier navigated back to the payment screen.
            const order = this.currentOrder;
            if (order) {
                const { amount } = getCharityData(order);
                if (amount > 0) {
                    this.charityState.donationAmount = amount;
                    this.charityState.isDonating = true;
                }
            }
        });
    },

    // ── Payment screen "Donate Change" button (Scenario B — customer overpaid) ─
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
        setCharityData(order, amount, getConfigAccountId(this.pos));
        this.charityState.donationAmount = amount;
        this.charityState.isDonating = true;
        this.notification.add(
            `${this.currencySymbol}${amount.toFixed(2)} will be donated to charity. Thank you!`,
            { type: "success", sticky: false }
        );
    },

    removeCharityDonation() {
        const order = this.currentOrder;
        if (order) clearCharityData(order);
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

// ── Define getters OUTSIDE patch() (esbuild/getter-syntax workaround) ─────
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
    // charityDonationAmount: reads charityStore (reactive) so the payment
    // screen template re-renders when charity is set from the order screen.
    charityDonationAmount: {
        get() {
            const order = this.currentOrder;
            return order ? (getCharityData(order).amount || 0) : 0;
        },
        configurable: true,
    },
    // changeAmount: measures real overpayment vs RAW total (not getDue).
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