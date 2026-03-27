/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { onMounted, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * POS Charity — Closing Register Integration (Odoo 19 CE)
 *
 * Patches ClosePosPopup directly so we can:
 *  1. Inject charityData (total + count) into the component state via RPC.
 *  2. Expose charityAmountFormatted for the template.
 *
 * The companion XML (charity_closing_popup.xml) uses t-inherit on
 * "point_of_sale.ClosePosPopup" to insert the charity section before
 * the closing-note textarea, reading charityData from the component.
 */
patch(ClosePosPopup.prototype, {

    setup() {
        super.setup(...arguments);

        // Reactive state for charity totals — starts empty/zero
        this.charityState = useState({
            total: 0,
            count: 0,
            loaded: false,
        });

        // We need orm service to call the backend
        this.orm = useService("orm");

        // Load charity totals as soon as the popup mounts
        onMounted(() => this._loadCharityTotals());
    },

    /**
     * Fetch live charity totals for the current session from the backend.
     * Uses the get_charity_totals() method on pos.session.
     */
    async _loadCharityTotals() {
        try {
            // Only fetch if charity is enabled on this POS config
            const pos = this.pos;
            if (!pos || !pos.config || !pos.config.charity_enabled) {
                return;
            }

            const sessionId = pos.session?.id;
            if (!sessionId) return;

            const result = await this.orm.call(
                "pos.session",
                "get_charity_totals",
                [[sessionId]]
            );

            if (result && result.total > 0) {
                this.charityState.total = result.total;
                this.charityState.count = result.count;
            }
            this.charityState.loaded = true;

        } catch (e) {
            console.warn("[POS Charity] Could not load charity totals for closing popup:", e);
            this.charityState.loaded = true;
        }
    },

    /**
     * Expose charityData to the template (mirrors old charityData prop pattern).
     * Returns null when charity is disabled or no donations found.
     */
    get charityData() {
        if (!this.charityState.loaded || this.charityState.total <= 0) {
            return null;
        }
        return {
            total: this.charityState.total,
            count: this.charityState.count,
        };
    },

    /**
     * Formatted charity amount string, e.g. "₹4.00"
     */
    get charityAmountFormatted() {
        const data = this.charityData;
        if (!data) return "";
        const pos = this.pos;
        const symbol = pos?.currency?.symbol || "₹";
        const dp = pos?.currency?.decimal_places ?? 2;
        return symbol + data.total.toFixed(dp);
    },
});