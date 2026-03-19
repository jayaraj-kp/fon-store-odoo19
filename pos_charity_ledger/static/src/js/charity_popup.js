/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class CharityDonationPopup extends Component {
    static template = "pos_charity_ledger.CharityDonationPopup";
    static components = { Dialog };
    static props = {
        title: { type: String, optional: true },
        changeAmount: { type: Number },
        currencySymbol: { type: String, optional: true },
        getPayload: Function,
        close: Function,
<<<<<<< HEAD
=======
    };
    static defaultProps = {
        title: "Donate to Charity",
        currencySymbol: "₹",
>>>>>>> b8cb2dc (custom)
    };
    static defaultProps = { title: "Donate to Charity", currencySymbol: "₹" };

<<<<<<< HEAD
    setup() { this.state = useState({ inputAmount: "", error: "" }); }

    get maxAmount() { return this.props.changeAmount || 0; }
    get symbol() { return this.props.currencySymbol || "₹"; }
    get displayAmount() { const v = parseFloat(this.state.inputAmount); return isNaN(v) ? "" : v.toFixed(2); }

    setAmount(amount) {
        if (amount > this.maxAmount) { this.state.error = `Maximum is ${this.symbol}${this.maxAmount.toFixed(2)}`; return; }
        this.state.error = ""; this.state.inputAmount = String(amount);
    }
=======
    setup() {
        this.state = useState({ inputAmount: "", error: "" });
    }

    get maxAmount() { return this.props.changeAmount || 0; }
    get symbol() { return this.props.currencySymbol || "₹"; }

    get displayAmount() {
        const val = parseFloat(this.state.inputAmount);
        return isNaN(val) ? "" : val.toFixed(2);
    }

    setAmount(amount) {
        if (amount > this.maxAmount) {
            this.state.error = `Maximum is ${this.symbol}${this.maxAmount.toFixed(2)}`;
            return;
        }
        this.state.error = "";
        this.state.inputAmount = String(amount);
    }

>>>>>>> b8cb2dc (custom)
    setFullChange() { this.setAmount(this.maxAmount); }

    confirm() {
        const val = parseFloat(this.state.inputAmount);
        if (isNaN(val) || val <= 0) { this.state.error = "Please enter a valid amount greater than 0."; return; }
        if (val > this.maxAmount) { this.state.error = `Maximum is ${this.symbol}${this.maxAmount.toFixed(2)}`; return; }
        this.props.getPayload({ confirmed: true, amount: val });
        this.props.close();
    }
<<<<<<< HEAD
    cancel() { this.props.getPayload({ confirmed: false, amount: 0 }); this.props.close(); }
=======

    cancel() {
        this.props.getPayload({ confirmed: false, amount: 0 });
        this.props.close();
    }

>>>>>>> b8cb2dc (custom)
    onInputChange(ev) { this.state.inputAmount = ev.target.value; this.state.error = ""; }

    pressKey(key) {
        if (key === "⌫") { this.state.inputAmount = this.state.inputAmount.slice(0, -1); }
        else if (key === ".") { if (!this.state.inputAmount.includes(".")) { this.state.inputAmount += this.state.inputAmount === "" ? "0." : "."; } }
        else { const p = this.state.inputAmount.split("."); if (p[1] && p[1].length >= 2) return; this.state.inputAmount += key; }
        this.state.error = "";
    }
}
