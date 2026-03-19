/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

/**
 * CharityDonationPopup
 * Used with makeAwaitable(this.dialog, CharityDonationPopup, props)
 */
export class CharityDonationPopup extends Component {
    static template = "pos_charity_ledger.CharityDonationPopup";
    static props = {
        title: { type: String, optional: true },
        changeAmount: { type: Number },
        currencySymbol: { type: String, optional: true },
        close: { type: Function },
    };
    static defaultProps = {
        title: _t("Donate to Charity"),
        currencySymbol: "₹",
    };

    setup() {
        this.state = useState({
            inputAmount: "",
            error: "",
        });
    }

    get maxAmount() {
        return this.props.changeAmount || 0;
    }

    get currencySymbol() {
        return this.props.currencySymbol || "₹";
    }

    setAmount(amount) {
        if (amount > this.maxAmount) {
            this.state.error = _t("Maximum donation is %s%s", this.currencySymbol, this.maxAmount.toFixed(2));
            return;
        }
        this.state.error = "";
        this.state.inputAmount = String(amount);
    }

    setFullChange() {
        this.setAmount(this.maxAmount);
    }

    _validateAmount() {
        const val = parseFloat(this.state.inputAmount);
        if (isNaN(val) || val <= 0) {
            this.state.error = _t("Please enter a valid amount greater than 0.");
            return false;
        }
        if (val > this.maxAmount) {
            this.state.error = _t("Maximum donation is %s%s", this.currencySymbol, this.maxAmount.toFixed(2));
            return false;
        }
        this.state.error = "";
        return true;
    }

    confirm() {
        if (!this._validateAmount()) return;
        this.props.close({ confirmed: true, amount: parseFloat(this.state.inputAmount) });
    }

    cancel() {
        this.props.close({ confirmed: false, amount: 0 });
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
            const parts = this.state.inputAmount.split(".");
            if (parts[1] && parts[1].length >= 2) return;
            this.state.inputAmount += key;
        }
        this.state.error = "";
    }
}
