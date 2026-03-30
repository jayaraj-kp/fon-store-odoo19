///** @odoo-module **/
//
//import { patch } from "@web/core/utils/patch";
//import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
//import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
//import { CharityDonationPopup } from "@pos_charity_ledger/js/charity_popup";
//import { useState } from "@odoo/owl";
//import { useService } from "@web/core/utils/hooks";
//import { PosOrder } from "@point_of_sale/app/models/pos_order";
//import { Component } from "@odoo/owl";
//
//// ─────────────────────────────────────────────────────────────────────────────
//// Extend POS Order serialization so charity metadata reaches the backend
//// ─────────────────────────────────────────────────────────────────────────────
//patch(PosOrder.prototype, {
//    serializeForORM(opts = {}) {
//        const data = super.serializeForORM(opts);
//        if (this._charity_donation_amount > 0) {
//            data.charity_donation_amount = this._charity_donation_amount;
//            data.charity_account_id      = this._charity_account_id || false;
//        }
//        return data;
//    },
//});
//
//// ─────────────────────────────────────────────────────────────────────────────
//// Helpers
//// ─────────────────────────────────────────────────────────────────────────────
//function getCurrencySymbol(pos) {
//    return pos.currency?.symbol || "₹";
//}
//
///**
// * Difference between the next whole rupee and the current total.
// * e.g.  297   → 3      (customer pays 300, donates 3)
// *       297.5 → 0.50
// *       300   → 0      (already whole, no auto round-off)
// */
//function computeRoundOff(total) {
//    const ceil = Math.ceil(total);
//    const diff = parseFloat((ceil - total).toFixed(2));
//    return diff > 0 ? diff : 0;
//}
//
//function getCurrentOrder(pos) {
//    try { const o = pos.get_order?.(); if (o) return o; } catch (_) {}
//    return pos.selectedOrder || pos.currentOrder || null;
//}
//
//function getLines(order) {
//    const raw = (typeof order.get_orderlines === "function" && order.get_orderlines())
//              || order.lines || order.orderlines || [];
//    return Array.isArray(raw) ? raw : [...raw];
//}
//
///**
// * Read the live order total.
// * Confirmed via console: order.totalDue is the reactive getter that
// * reads _prices.original.taxDetails.total_amount_currency.
// */
//function getOrderTotal(order) {
//    if (typeof order.totalDue === "number" && order.totalDue > 0) return order.totalDue;
//    return order._prices?.original?.taxDetails?.total_amount_currency || 0;
//}
//
//// ─────────────────────────────────────────────────────────────────────────────
//// Core: add charity amount directly to the order line price
////
//// Confirmed working via console test:
////   line.setUnitPrice(newPrice)         → reactive price_unit setter
////   order.triggerRecomputeAllPrices()   → recalculates _prices → totalDue updates
////
//// Result: totalDue 297 → 300 instantly, payment screen shows ₹300,
////         cash drawer receives ₹300, closing register shows full amount.
//// ─────────────────────────────────────────────────────────────────────────────
//function applyCharityToOrder(order, donationAmount) {
//    const lines = getLines(order);
//    if (!lines.length) return false;
//
//    // Use the last line so the donation bump appears on the most recent item
//    const line = lines[lines.length - 1];
//
//    // Save the original price once (guards against double-apply)
//    if (line._charity_original_price === undefined) {
//        line._charity_original_price = line.price_unit;
//    }
//
//    line.setUnitPrice(line._charity_original_price + donationAmount);
//    order.triggerRecomputeAllPrices();
//    return true;
//}
//
//function removeCharityFromOrder(order) {
//    const lines = getLines(order);
//    for (const line of lines) {
//        if (line._charity_original_price !== undefined) {
//            line.setUnitPrice(line._charity_original_price);
//            delete line._charity_original_price;
//        }
//    }
//    order.triggerRecomputeAllPrices();
//}
//
//// ─────────────────────────────────────────────────────────────────────────────
//// Order Screen Charity Button Component
//// ─────────────────────────────────────────────────────────────────────────────
//export class CharityOrderButton extends Component {
//    static template = "pos_charity_ledger.CharityOrderButton";
//    static props = {};
//
//    setup() {
//        try { this.pos = useService("pos"); } catch (_) { this.pos = this.env.pos; }
//        this.dialog       = useService("dialog");
//        this.notification = useService("notification");
//        this.charityState = useState({ donationAmount: 0, isDonating: false });
//    }
//
//    get charityEnabled() {
//        return this.pos.config.charity_enabled && this.pos.config.charity_account_id;
//    }
//
//    get charityButtonLabel() {
//        return this.pos.config.charity_button_label || "Donate to Charity";
//    }
//
//    get currencySymbol() {
//        return getCurrencySymbol(this.pos);
//    }
//
//    get currentOrder() {
//        return getCurrentOrder(this.pos);
//    }
//
//    get orderRoundOffAmount() {
//        const order = this.currentOrder;
//        if (!order) return 0;
//        return computeRoundOff(getOrderTotal(order));
//    }
//
//    async openOrderCharityPopup() {
//        if (!this.charityEnabled) return;
//        const order = this.currentOrder;
//        if (!order) {
//            this.notification.add("No active order found.", { type: "warning" });
//            return;
//        }
//
//        const total = getOrderTotal(order);
//        if (total <= 0) {
//            this.notification.add("Please add products before donating.", { type: "warning" });
//            return;
//        }
//
//        const roundOff  = computeRoundOff(total);
//        // Has decimal gap → cap at that gap.  Already whole → no cap, cashier enters freely.
//        const maxDonate  = roundOff > 0 ? roundOff : Infinity;
//        const ceilAmount = roundOff > 0 ? roundOff : 1;
//
//        const result = await makeAwaitable(this.dialog, CharityDonationPopup, {
//            title:          this.charityButtonLabel,
//            changeAmount:   maxDonate,
//            roundOffAmount: roundOff,
//            ceilAmount:     ceilAmount,
//            currencySymbol: this.currencySymbol,
//        });
//
//        if (result?.confirmed && result.amount > 0) {
//            this._applyDonation(order, result.amount);
//        }
//    }
//
//    _applyDonation(order, amount) {
//        const accountId = Array.isArray(this.pos.config.charity_account_id)
//            ? this.pos.config.charity_account_id[0]
//            : this.pos.config.charity_account_id;
//
//        // Bump the line price → totalDue updates instantly (297 → 300)
//        applyCharityToOrder(order, amount);
//
//        // Store metadata so serializeForORM sends it to the backend
//        order._charity_donation_amount = amount;
//        order._charity_account_id      = accountId;
//
//        this.charityState.donationAmount = amount;
//        this.charityState.isDonating     = true;
//
//        const newTotal = getOrderTotal(order);
//        this.notification.add(
//            `❤ ${this.currencySymbol}${amount.toFixed(2)} charity added — collect ${this.currencySymbol}${newTotal.toFixed(2)}`,
//            { type: "success", sticky: false }
//        );
//    }
//
//    removeOrderCharityDonation() {
//        const order = this.currentOrder;
//        if (order) {
//            // Restore original line price → totalDue goes back to 297
//            removeCharityFromOrder(order);
//            order._charity_donation_amount = 0;
//            order._charity_account_id      = null;
//        }
//        this.charityState.donationAmount = 0;
//        this.charityState.isDonating     = false;
//    }
//}
//
//// ─────────────────────────────────────────────────────────────────────────────
//// Payment Screen patch
//// Donation here comes from already-entered change — does NOT change order total
//// ─────────────────────────────────────────────────────────────────────────────
//patch(PaymentScreen.prototype, {
//    setup() {
//        super.setup(...arguments);
//        this.charityState = useState({ donationAmount: 0, isDonating: false });
//    },
//
//    get charityEnabled() {
//        return this.pos.config.charity_enabled && this.pos.config.charity_account_id;
//    },
//
//    get charityButtonLabel() {
//        return this.pos.config.charity_button_label || "Donate to Charity";
//    },
//
//    get changeAmount() {
//        const order = this.currentOrder;
//        if (!order) return 0;
//        const totalDue  = order.totalDue || 0;
//        const totalPaid = (order.payment_ids || []).reduce(
//            (sum, line) => sum + (line.getAmount ? line.getAmount() : (line.amount || 0)), 0
//        );
//        const change = totalPaid - totalDue;
//        return change > 0 ? parseFloat(change.toFixed(2)) : 0;
//    },
//
//    get currencySymbol() {
//        return getCurrencySymbol(this.pos);
//    },
//
//    async openCharityPopup() {
//        if (!this.charityEnabled) return;
//        const changeAmt = this.changeAmount;
//        if (changeAmt <= 0) {
//            this.notification.add(
//                "No change to donate. Use the ❤ Charity button on the order screen to round up before payment.",
//                { type: "warning", sticky: false }
//            );
//            return;
//        }
//        const result = await makeAwaitable(this.dialog, CharityDonationPopup, {
//            title:          this.charityButtonLabel,
//            changeAmount:   changeAmt,
//            roundOffAmount: 0,
//            currencySymbol: this.currencySymbol,
//        });
//        if (result?.confirmed && result.amount > 0) {
//            this._applyCharityDonation(result.amount);
//        }
//    },
//
//    _applyCharityDonation(amount) {
//        const order = this.currentOrder;
//        if (!order) return;
//        const accountId = Array.isArray(this.pos.config.charity_account_id)
//            ? this.pos.config.charity_account_id[0]
//            : this.pos.config.charity_account_id;
//        order._charity_donation_amount = amount;
//        order._charity_account_id      = accountId;
//        this.charityState.donationAmount = amount;
//        this.charityState.isDonating     = true;
//        this.notification.add(
//            `${this.currencySymbol}${amount.toFixed(2)} will be donated to charity. Thank you!`,
//            { type: "success", sticky: false }
//        );
//    },
//
//    removeCharityDonation() {
//        const order = this.currentOrder;
//        if (order) {
//            order._charity_donation_amount = 0;
//            order._charity_account_id      = null;
//        }
//        this.charityState.donationAmount = 0;
//        this.charityState.isDonating     = false;
//    },
//
//    async validateOrder(isForceValidate) {
//        const result = await super.validateOrder(isForceValidate);
//        this.charityState.donationAmount = 0;
//        this.charityState.isDonating     = false;
//        return result;
//    },
//});

/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { CharityDonationPopup } from "@pos_charity_ledger/js/charity_popup";
import { useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { Component } from "@odoo/owl";

// ─────────────────────────────────────────────────────────────────────────────
// Extend POS Order serialization so charity metadata reaches the backend
// ─────────────────────────────────────────────────────────────────────────────
patch(PosOrder.prototype, {
    serializeForORM(opts = {}) {
        const data = super.serializeForORM(opts);
        if (this._charity_donation_amount > 0) {
            data.charity_donation_amount = this._charity_donation_amount;
            data.charity_account_id      = this._charity_account_id || false;
        }
        return data;
    },
});

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────
function getCurrencySymbol(pos) {
    return pos.currency?.symbol || "₹";
}

/**
 * Difference to next whole rupee.
 * e.g. 997 → 3  |  997.50 → 0.50  |  1000 → 0
 */
function computeRoundOff(total) {
    const ceil = Math.ceil(total);
    const diff = parseFloat((ceil - total).toFixed(2));
    return diff > 0 ? diff : 0;
}

function getCurrentOrder(pos) {
    try { const o = pos.get_order?.(); if (o) return o; } catch (_) {}
    return pos.selectedOrder || pos.currentOrder || null;
}

function getLines(order) {
    const raw = (typeof order.get_orderlines === "function" && order.get_orderlines())
              || order.lines || order.orderlines || [];
    return Array.isArray(raw) ? raw : [...raw];
}

/** Read live order total via totalDue (confirmed reactive getter) */
function getOrderTotal(order) {
    if (typeof order.totalDue === "number" && order.totalDue > 0) return order.totalDue;
    return order._prices?.original?.taxDetails?.total_amount_currency || 0;
}

/**
 * Find the CHARITY_ROUNDOFF product from the POS loaded product list.
 * The product is loaded into the POS via _loader_params_product_product
 * override in pos_session.py.
 */
function getCharityProduct(pos) {
    // Odoo 19 CE stores products in pos.models["product.product"]
    const model = pos.models?.["product.product"];
    if (model) {
        const all = typeof model.getAll === "function" ? model.getAll()
                  : Object.values(model.records || {});
        const found = all.find(p => p.default_code === "CHARITY_ROUNDOFF");
        if (found) return found;
    }
    // Fallback: search all loaded records
    for (const key of Object.keys(pos.models || {})) {
        if (!key.includes("product")) continue;
        const m = pos.models[key];
        const records = typeof m.getAll === "function" ? m.getAll()
                      : Object.values(m.records || {});
        const found = records.find(p => p.default_code === "CHARITY_ROUNDOFF");
        if (found) return found;
    }
    return null;
}

/**
 * Add the charity round-off as a SEPARATE product line on the order.
 *
 * Why a product line (not setUnitPrice)?
 *   setUnitPrice(997+3) → inflates the existing line → invoice posts
 *   ₹1,000 to product sales account → ₹3 double-counted in revenue ❌
 *
 *   A separate CHARITY_ROUNDOFF product line → invoice splits correctly:
 *     400000 Product Sales  CREDIT ₹997  ✅
 *     201002 Charity GL     CREDIT ₹3   ✅  (income account on product)
 *     121000 Receivable     DEBIT  ₹1,000 ✅
 */
function addCharityLineToOrder(pos, order, amount) {
    // Remove any existing charity line first (guard against double-click)
    removeCharityLineFromOrder(order);

    const product = getCharityProduct(pos);
    if (!product) {
        console.error(
            "[CharityButton] CHARITY_ROUNDOFF product not found in POS. " +
            "Make sure the module is upgraded and the POS session is restarted."
        );
        return false;
    }

    try {
        if (typeof order.add_product === "function") {
            order.add_product(product, {
                quantity: 1,
                price:    amount,
            });
            // Tag the newly added line so we can find/remove it
            const lines = getLines(order);
            const last  = lines[lines.length - 1];
            if (last) {
                last._is_charity_line = true;
                console.log(
                    "[CharityButton] Charity line added. totalDue now:",
                    getOrderTotal(order)
                );
            }
            return true;
        }
    } catch (e) {
        console.error("[CharityButton] Error adding charity line:", e);
    }
    return false;
}

function removeCharityLineFromOrder(order) {
    const lines = getLines(order);
    for (const line of lines) {
        if (line._is_charity_line) {
            try {
                if (typeof order.remove_orderline === "function") {
                    order.remove_orderline(line);
                } else if (typeof line.remove === "function") {
                    line.remove();
                } else if (typeof line.delete === "function") {
                    line.delete();
                }
            } catch (e) {
                console.warn("[CharityButton] Error removing charity line:", e);
            }
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Order Screen Charity Button Component
// ─────────────────────────────────────────────────────────────────────────────
export class CharityOrderButton extends Component {
    static template = "pos_charity_ledger.CharityOrderButton";
    static props = {};

    setup() {
        try { this.pos = useService("pos"); } catch (_) { this.pos = this.env.pos; }
        this.dialog       = useService("dialog");
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

        const roundOff   = computeRoundOff(total);
        const maxDonate  = roundOff > 0 ? roundOff : Infinity;
        const ceilAmount = roundOff > 0 ? roundOff : 1;

        const result = await makeAwaitable(this.dialog, CharityDonationPopup, {
            title:          this.charityButtonLabel,
            changeAmount:   maxDonate,
            roundOffAmount: roundOff,
            ceilAmount:     ceilAmount,
            currencySymbol: this.currencySymbol,
        });

        if (result?.confirmed && result.amount > 0) {
            this._applyDonation(order, result.amount);
        }
    }

    _applyDonation(order, amount) {
        const accountId = Array.isArray(this.pos.config.charity_account_id)
            ? this.pos.config.charity_account_id[0]
            : this.pos.config.charity_account_id;

        // Add CHARITY_ROUNDOFF product line → totalDue increases correctly
        // AND invoice maps ₹3 to 201002 Charity account (not product sales)
        const lineAdded = addCharityLineToOrder(this.pos, order, amount);

        if (!lineAdded) {
            this.notification.add(
                "Charity product not found. Please restart the POS session.",
                { type: "danger", sticky: true }
            );
            return;
        }

        // Store metadata for backend serialization
        order._charity_donation_amount = amount;
        order._charity_account_id      = accountId;

        this.charityState.donationAmount = amount;
        this.charityState.isDonating     = true;

        const newTotal = getOrderTotal(order);
        this.notification.add(
            `❤ ${this.currencySymbol}${amount.toFixed(2)} charity added — collect ${this.currencySymbol}${newTotal.toFixed(2)}`,
            { type: "success", sticky: false }
        );
    }

    removeOrderCharityDonation() {
        const order = this.currentOrder;
        if (order) {
            removeCharityLineFromOrder(order);
            order._charity_donation_amount = 0;
            order._charity_account_id      = null;
        }
        this.charityState.donationAmount = 0;
        this.charityState.isDonating     = false;
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Payment Screen patch
// ─────────────────────────────────────────────────────────────────────────────
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
        const totalDue  = order.totalDue || 0;
        const totalPaid = (order.payment_ids || []).reduce(
            (sum, line) => sum + (line.getAmount ? line.getAmount() : (line.amount || 0)), 0
        );
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
            this.notification.add(
                "No change to donate. Use the ❤ Charity button on the order screen to round up before payment.",
                { type: "warning", sticky: false }
            );
            return;
        }
        const result = await makeAwaitable(this.dialog, CharityDonationPopup, {
            title:          this.charityButtonLabel,
            changeAmount:   changeAmt,
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
        const accountId = Array.isArray(this.pos.config.charity_account_id)
            ? this.pos.config.charity_account_id[0]
            : this.pos.config.charity_account_id;
        order._charity_donation_amount = amount;
        order._charity_account_id      = accountId;
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
            order._charity_donation_amount = 0;
            order._charity_account_id      = null;
        }
        this.charityState.donationAmount = 0;
        this.charityState.isDonating     = false;
    },

    async validateOrder(isForceValidate) {
        const result = await super.validateOrder(isForceValidate);
        this.charityState.donationAmount = 0;
        this.charityState.isDonating     = false;
        return result;
    },
});