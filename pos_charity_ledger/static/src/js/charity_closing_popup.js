/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

/**
 * POS Charity — Closing Reminder
 *
 * We patch PosStore.closePos() so that BEFORE the closing register dialog
 * opens, a sticky warning tells the cashier exactly how much charity cash
 * to physically remove from the drawer before counting.
 *
 * Why PosStore instead of ClosePosPopup?
 * ClosePosPopup lives in a different asset bundle in Odoo 19 CE and cannot
 * be imported from the POS session bundle — doing so causes the
 * "module not defined" error. PosStore is part of the core POS session
 * bundle and is safe to patch.
 */
patch(PosStore.prototype, {

    /**
     * Override closePos to inject the charity reminder before
     * the closing dialog is shown to the cashier.
     */
    async closePos() {
        await this._showCharityCloseReminder();
        return super.closePos(...arguments);
    },

    /**
     * Fetch charity totals for this session via RPC and display
     * a sticky notification if there are any donations.
     *
     * Using an RPC call (rather than cached session data) guarantees
     * we always show the live total even for donations made after
     * the session was first loaded.
     */
    async _showCharityCloseReminder() {
        // Skip if charity is not enabled for this POS config
        if (!this.config || !this.config.charity_enabled) {
            return;
        }

        try {
            const result = await this.env.services.orm.call(
                "pos.session",
                "get_charity_totals",
                [[this.session.id]]
            );

            if (!result || !(result.total > 0)) {
                return;
            }

            const currency      = this.currency;
            const symbol        = (currency && currency.symbol)               || "₹";
            const dp            = (currency && currency.decimal_places != null)
                                      ? currency.decimal_places : 2;
            const total         = result.total.toFixed(dp);
            const count         = result.count;
            const donationWord  = count === 1 ? "donation" : "donations";

            this.env.services.notification.add(
                `❤  Charity collected this session: ${symbol}${total}` +
                ` (${count} ${donationWord}). ` +
                `Please remove ${symbol}${total} from the cash drawer before counting.`,
                {
                    title:  "Charity Donations — Action Required",
                    type:   "warning",
                    sticky: true,   // stays visible until cashier dismisses it
                }
            );

        } catch (e) {
            // Non-fatal — log and continue with normal close flow
            console.warn("[POS Charity] Could not load charity totals for close reminder:", e);
        }
    },
});