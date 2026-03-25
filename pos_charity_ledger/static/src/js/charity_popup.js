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
        currencySymbol: { type: String, optional: true },
        getPayload: Function,
        close: Function,
    };
    static defaultProps = { title: "Donate to Charity", currencySymbol: "₹", roundOffAmount: 0 };

    setup() {
        this.state = useState({ inputAmount: "", error: "" });
    }

    get maxAmount() { return this.props.changeAmount || 0; }
    get symbol() { return this.props.currencySymbol || "₹"; }
    get roundOff() { return this.props.roundOffAmount || 0; }

    get displayAmount() {
        const v = parseFloat(this.state.inputAmount);
        return isNaN(v) ? "" : v.toFixed(2);
    }

    setAmount(amount) {
        if (amount > this.maxAmount) {
            this.state.error = "Maximum is " + this.symbol + this.maxAmount.toFixed(2);
            return;
        }
        this.state.error = "";
        this.state.inputAmount = String(amount);
    }

    setFullChange() { this.setAmount(this.maxAmount); }

    setRoundOff() {
        if (this.roundOff > 0) {
            this.setAmount(parseFloat(this.roundOff.toFixed(2)));
        }
    }

    confirm() {
        const val = parseFloat(this.state.inputAmount);
        if (isNaN(val) || val <= 0) {
            this.state.error = "Please enter a valid amount greater than 0.";
            return;
        }
        if (val > this.maxAmount) {
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
        } else if (key === ".") {
            if (!this.state.inputAmount.includes(".")) {
                this.state.inputAmount += this.state.inputAmount === "" ? "0." : ".";
            }
        } else {
            const p = this.state.inputAmount.split(".");
            if (p[1] && p[1].length >= 2) return;
            this.state.inputAmount += key;
        }
        this.state.error = "";
    }
}
