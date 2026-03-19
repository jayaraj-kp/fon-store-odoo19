/** @odoo-module **/

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

/**
 * CharityDonationPopup
 *
 * A popup shown when the cashier clicks the "Donate to Charity" button.
 * Lets the cashier enter an amount (up to the available change).
 *
 * Props:
 *  - title: string
 *  - changeAmount: number (max they can donate)
 *  - currency: currency object
 */
export class CharityDonationPopup extends AbstractAwaitablePopup {
    static template = "pos_charity_ledger.CharityDonationPopup";
    static defaultProps = {
        confirmText: _t("Donate"),
        cancelText: _t("Cancel"),
        title: _t("Charity Donation"),
        body: "",
    };

    setup() {
        super.setup();
        this.state = useState({
            inputAmount: "",
            error: "",
        });
    }

    get maxAmount() {
        return this.props.changeAmount || 0;
    }

    get currencySymbol() {
        return this.props.currency?.symbol || "₹";
    }

    /**
     * Set a quick amount button value.
     */
    setAmount(amount) {
        if (amount > this.maxAmount) {
            this.state.error = `Maximum donation is ${this.currencySymbol}${this.maxAmount.toFixed(2)}`;
            return;
        }
        this.state.error = "";
        this.state.inputAmount = amount.toString();
    }

    /**
     * Set full change as donation amount.
     */
    setFullChange() {
        this.setAmount(this.maxAmount);
    }

    /**
     * Validate the entered amount.
     */
    _validateAmount() {
        const val = parseFloat(this.state.inputAmount);
        if (isNaN(val) || val <= 0) {
            this.state.error = "Please enter a valid amount greater than 0.";
            return false;
        }
        if (val > this.maxAmount) {
            this.state.error = `Maximum donation is ${this.currencySymbol}${this.maxAmount.toFixed(2)}`;
            return false;
        }
        this.state.error = "";
        return true;
    }

    getPayload() {
        return {
            amount: parseFloat(this.state.inputAmount),
        };
    }

    async confirm() {
        if (!this._validateAmount()) return;
        super.confirm();
    }

    /**
     * Handle numpad/keyboard input.
     */
    onInputChange(ev) {
        this.state.inputAmount = ev.target.value;
        this.state.error = "";
    }

    /**
     * Handle numpad digit press.
     */
    pressKey(key) {
        if (key === "⌫") {
            this.state.inputAmount = this.state.inputAmount.slice(0, -1);
        } else if (key === ".") {
            if (!this.state.inputAmount.includes(".")) {
                this.state.inputAmount += this.state.inputAmount === "" ? "0." : ".";
            }
        } else {
            // Prevent more than 2 decimal places
            const parts = this.state.inputAmount.split(".");
            if (parts[1] && parts[1].length >= 2) return;
            this.state.inputAmount += key;
        }
        this.state.error = "";
    }
}
