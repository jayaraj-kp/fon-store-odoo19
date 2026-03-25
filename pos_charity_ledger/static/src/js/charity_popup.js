/////** @odoo-module **/
////
////import { Component, useState } from "@odoo/owl";
////import { Dialog } from "@web/core/dialog/dialog";
////
////export class CharityDonationPopup extends Component {
////    static template = "pos_charity_ledger.CharityDonationPopup";
////    static components = { Dialog };
////    static props = {
////        title: { type: String, optional: true },
////        changeAmount: { type: Number },
////        roundOffAmount: { type: Number, optional: true },
////        currencySymbol: { type: String, optional: true },
////        getPayload: Function,
////        close: Function,
////    };
////    static defaultProps = { title: "Donate to Charity", currencySymbol: "₹", roundOffAmount: 0 };
////
////    setup() {
////        this.state = useState({ inputAmount: "", error: "" });
////    }
////
////    /** True when there is no upper cap (order total is a whole number) */
////    get hasNoMax() { return !isFinite(this.props.changeAmount); }
////
////    get maxAmount() { return this.props.changeAmount || 0; }
////    get symbol() { return this.props.currencySymbol || "₹"; }
////    get roundOff() { return this.props.roundOffAmount || 0; }
////
////    get displayAmount() {
////        const v = parseFloat(this.state.inputAmount);
////        return isNaN(v) ? "" : v.toFixed(2);
////    }
////
////    setAmount(amount) {
////        // Only enforce the max when there is a finite cap
////        if (!this.hasNoMax && amount > this.maxAmount) {
////            this.state.error = "Maximum is " + this.symbol + this.maxAmount.toFixed(2);
////            return;
////        }
////        this.state.error = "";
////        this.state.inputAmount = String(amount);
////    }
////
////    /** Only shown in template when hasNoMax is false */
////    setFullChange() { this.setAmount(this.maxAmount); }
////
////    setRoundOff() {
////        if (this.roundOff > 0) {
////            this.setAmount(parseFloat(this.roundOff.toFixed(2)));
////        }
////    }
////
////    confirm() {
////        const val = parseFloat(this.state.inputAmount);
////        if (isNaN(val) || val <= 0) {
////            this.state.error = "Please enter a valid amount greater than 0.";
////            return;
////        }
////        // Only block submission when there is a finite cap
////        if (!this.hasNoMax && val > this.maxAmount) {
////            this.state.error = "Maximum is " + this.symbol + this.maxAmount.toFixed(2);
////            return;
////        }
////        this.props.getPayload({ confirmed: true, amount: val });
////        this.props.close();
////    }
////
////    cancel() {
////        this.props.getPayload({ confirmed: false, amount: 0 });
////        this.props.close();
////    }
////
////    onInputChange(ev) {
////        this.state.inputAmount = ev.target.value;
////        this.state.error = "";
////    }
////
////    pressKey(key) {
////        if (key === "⌫") {
////            this.state.inputAmount = this.state.inputAmount.slice(0, -1);
////            this.state.error = "";
////            return;
////        }
////        if (key === ".") {
////            if (!this.state.inputAmount.includes(".")) {
////                this.state.inputAmount += this.state.inputAmount === "" ? "0." : ".";
////            }
////            this.state.error = "";
////            return;
////        }
////        // Build candidate and reject if it exceeds the finite cap
////        const p = this.state.inputAmount.split(".");
////        if (p[1] && p[1].length >= 2) return;
////        const candidate = this.state.inputAmount + key;
////        const candidateVal = parseFloat(candidate);
////        if (!this.hasNoMax && !isNaN(candidateVal) && candidateVal > this.maxAmount) {
////            this.state.error = "Maximum is " + this.symbol + this.maxAmount.toFixed(2);
////            return;
////        }
////        this.state.inputAmount = candidate;
////        this.state.error = "";
////    }
////}
///** @odoo-module **/
//
//import { Component, useState } from "@odoo/owl";
//import { Dialog } from "@web/core/dialog/dialog";
//
//export class CharityDonationPopup extends Component {
//    static template = "pos_charity_ledger.CharityDonationPopup";
//    static components = { Dialog };
//    static props = {
//        title: { type: String, optional: true },
//        changeAmount: { type: Number },
//        roundOffAmount: { type: Number, optional: true },
//        ceilAmount: { type: Number, optional: true },
//        currencySymbol: { type: String, optional: true },
//        getPayload: Function,
//        close: Function,
//    };
//    static defaultProps = {
//        title: "Donate to Charity",
//        currencySymbol: "₹",
//        roundOffAmount: 0,
//        ceilAmount: 1,
//    };
//
//    setup() {
//        this.state = useState({ inputAmount: "", error: "" });
//    }
//
//    /** True when there is no upper cap (order total is a whole number) */
//    get hasNoMax() { return !isFinite(this.props.changeAmount); }
//
//    get maxAmount() { return this.props.changeAmount || 0; }
//    get symbol() { return this.props.currencySymbol || "₹"; }
//    get roundOff() { return this.props.roundOffAmount || 0; }
//
//    /** Amount for the one-tap Full Change button (e.g. ₹1 for ₹999, ₹0.55 for ₹693.45) */
//    get ceilAmount() { return this.props.ceilAmount || 1; }
//
//    get displayAmount() {
//        const v = parseFloat(this.state.inputAmount);
//        return isNaN(v) ? "" : v.toFixed(2);
//    }
//
//    setAmount(amount) {
//        if (!this.hasNoMax && amount > this.maxAmount) {
//            this.state.error = "Maximum is " + this.symbol + this.maxAmount.toFixed(2);
//            return;
//        }
//        this.state.error = "";
//        this.state.inputAmount = String(amount);
//    }
//
//    /** Used when cap is finite (round-off scenario) — sets amount to cap */
//    setFullChange() { this.setAmount(this.maxAmount); }
//
//    setRoundOff() {
//        if (this.roundOff > 0) {
//            this.setAmount(parseFloat(this.roundOff.toFixed(2)));
//        }
//    }
//
//    /**
//     * One-tap Full Change for whole-number totals (e.g. ₹999 → donate ₹1 instantly).
//     * Sets the amount AND immediately confirms — no need to press Donate.
//     */
//    confirmFullChange() {
//        const amount = parseFloat(this.ceilAmount.toFixed(2));
//        if (amount > 0) {
//            this.props.getPayload({ confirmed: true, amount });
//            this.props.close();
//        }
//    }
//
//    confirm() {
//        const val = parseFloat(this.state.inputAmount);
//        if (isNaN(val) || val <= 0) {
//            this.state.error = "Please enter a valid amount greater than 0.";
//            return;
//        }
//        if (!this.hasNoMax && val > this.maxAmount) {
//            this.state.error = "Maximum is " + this.symbol + this.maxAmount.toFixed(2);
//            return;
//        }
//        this.props.getPayload({ confirmed: true, amount: val });
//        this.props.close();
//    }
//
//    cancel() {
//        this.props.getPayload({ confirmed: false, amount: 0 });
//        this.props.close();
//    }
//
//    onInputChange(ev) {
//        this.state.inputAmount = ev.target.value;
//        this.state.error = "";
//    }
//
//    pressKey(key) {
//        if (key === "⌫") {
//            this.state.inputAmount = this.state.inputAmount.slice(0, -1);
//            this.state.error = "";
//            return;
//        }
//        if (key === ".") {
//            if (!this.state.inputAmount.includes(".")) {
//                this.state.inputAmount += this.state.inputAmount === "" ? "0." : ".";
//            }
//            this.state.error = "";
//            return;
//        }
//        // Build candidate and reject if it exceeds the finite cap
//        const p = this.state.inputAmount.split(".");
//        if (p[1] && p[1].length >= 2) return;
//        const candidate = this.state.inputAmount + key;
//        const candidateVal = parseFloat(candidate);
//        if (!this.hasNoMax && !isNaN(candidateVal) && candidateVal > this.maxAmount) {
//            this.state.error = "Maximum is " + this.symbol + this.maxAmount.toFixed(2);
//            return;
//        }
//        this.state.inputAmount = candidate;
//        this.state.error = "";
//    }
//}
/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class CharityDonationPopup extends Component {
    static template = "pos_charity_ledger.CharityDonationPopup";
    static components = { Dialog };
    static props = {
        title: { type: String, optional: true },
        changeAmount: { type: Number },
        roundOffAmount: { type: Number, optional: true },
        ceilAmount: { type: Number, optional: true },
        currencySymbol: { type: String, optional: true },
        getPayload: Function,
        close: Function,
    };
    static defaultProps = {
        title: "Donate to Charity",
        currencySymbol: "₹",
        roundOffAmount: 0,
        ceilAmount: 1,
    };

    setup() {
        this.state = useState({ inputAmount: "", error: "" });
    }

    /** True when there is no upper cap (order total is a whole number) */
    get hasNoMax() { return !isFinite(this.props.changeAmount); }

    get maxAmount() { return this.props.changeAmount || 0; }
    get symbol() { return this.props.currencySymbol || "₹"; }
    get roundOff() { return this.props.roundOffAmount || 0; }

    /** Amount for the one-tap Full Change button (e.g. ₹1 for ₹999, ₹0.55 for ₹693.45) */
    get ceilAmount() { return this.props.ceilAmount || 1; }

    get displayAmount() {
        const v = parseFloat(this.state.inputAmount);
        return isNaN(v) ? "" : v.toFixed(2);
    }

    setAmount(amount) {
        if (!this.hasNoMax && amount > this.maxAmount) {
            this.state.error = "Maximum is " + this.symbol + this.maxAmount.toFixed(2);
            return;
        }
        this.state.error = "";
        this.state.inputAmount = String(amount);
    }

    /** Used when cap is finite (round-off scenario) — sets amount to cap */
    setFullChange() { this.setAmount(this.maxAmount); }

    /**
     * One-tap Round Off — sets amount AND confirms instantly.
     * No need to press the Donate button after.
     */
    confirmRoundOff() {
        const amount = parseFloat(this.roundOff.toFixed(2));
        if (amount > 0) {
            this.props.getPayload({ confirmed: true, amount });
            this.props.close();
        }
    }

    /**
     * One-tap Full Change for whole-number totals (e.g. ₹999 → donate ₹1 instantly).
     * Sets the amount AND immediately confirms — no need to press Donate.
     */
    confirmFullChange() {
        const amount = parseFloat(this.ceilAmount.toFixed(2));
        if (amount > 0) {
            this.props.getPayload({ confirmed: true, amount });
            this.props.close();
        }
    }

    confirm() {
        const val = parseFloat(this.state.inputAmount);
        if (isNaN(val) || val <= 0) {
            this.state.error = "Please enter a valid amount greater than 0.";
            return;
        }
        if (!this.hasNoMax && val > this.maxAmount) {
            this.state.error = "Maximum is " + this.symbol + this.maxAmount.toFixed(2);
            return;
        }
        this.props.getPayload({ confirmed: true, amount: val });
        this.props.close();
    }

    cancel() {
        this.props.getPayload({ confirmed: false, amount: 0 });
        this.props.close();
    }

    onInputChange(ev) {
        this.state.inputAmount = ev.target.value;
        this.state.error = "";
    }

    pressKey(key) {
        if (key === "⌫") {
            this.state.inputAmount = this.state.inputAmount.slice(0, -1);
            this.state.error = "";
            return;
        }
        if (key === ".") {
            if (!this.state.inputAmount.includes(".")) {
                this.state.inputAmount += this.state.inputAmount === "" ? "0." : ".";
            }
            this.state.error = "";
            return;
        }
        // Build candidate and reject if it exceeds the finite cap
        const p = this.state.inputAmount.split(".");
        if (p[1] && p[1].length >= 2) return;
        const candidate = this.state.inputAmount + key;
        const candidateVal = parseFloat(candidate);
        if (!this.hasNoMax && !isNaN(candidateVal) && candidateVal > this.maxAmount) {
            this.state.error = "Maximum is " + this.symbol + this.maxAmount.toFixed(2);
            return;
        }
        this.state.inputAmount = candidate;
        this.state.error = "";
    }
}