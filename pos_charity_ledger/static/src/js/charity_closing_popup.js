/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ClosePosPopup } from "@point_of_sale/app/screens/closing_popup/closing_popup";
import { useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Patch the POS Closing Register popup to show charity donation totals.
 *
 * When the cashier opens "Close Register" this patch:
 *  1. Makes an RPC call to pos.session.get_charity_totals() to get the
 *     live total (avoids stale cached values).
 *  2. Exposes charityData (reactive) so the template can render the section.
 *  3. Shows the physical cash hint so the cashier knows to remove the
 *     charity amount before counting the drawer.
 */
patch(ClosePosPopup.prototype, {
    setup() {
        super.setup();
        // Separate orm reference to avoid name collisions with existing service refs
        this._charityOrm = useService("orm");
        // Reactive state — updates trigger template re-render automatically
        this.charityData = useState({ total: 0, count: 0, loaded: false });

        onMounted(async () => {
            try {
                const sessionId = this.pos.session.id;
                const result = await this._charityOrm.call(
                    "pos.session",
                    "get_charity_totals",
                    [[sessionId]],
                );
                if (result) {
                    this.charityData.total = result.total || 0;
                    this.charityData.count = result.count || 0;
                    this.charityData.loaded = true;
                }
            } catch (e) {
                console.warn("[POS Charity] Could not load charity totals:", e);
            }
        });
    },

    /** Formatted charity total using POS currency settings */
    get charityAmountFormatted() {
        const amount = this.charityData ? this.charityData.total : 0;
        const currency = this.pos.currency;
        const symbol = (currency && currency.symbol) || "₹";
        const decimals =
            currency && currency.decimal_places != null
                ? currency.decimal_places
                : 2;
        return symbol + amount.toFixed(decimals);
    },
});