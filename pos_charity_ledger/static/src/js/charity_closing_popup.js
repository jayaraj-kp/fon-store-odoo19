/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

/**
 * POS Charity — Closing Register Reminder  (Odoo 19 CE)
 *
 * WHY we patch PosStore and NOT ClosePosPopup:
 * -----------------------------------------------
 * In Odoo 19 CE the Closing Register dialog (ClosePosPopup) is rendered
 * inside the "point_of_sale._assets_pos_closing" bundle, which is a
 * SEPARATE lazy-loaded bundle.  Any attempt to import it from the main
 * "point_of_sale._assets_pos" bundle causes:
 *
 *   "The following modules are needed but have not been defined …
 *    @point_of_sale/app/navbar/closing_popup/closing_popup"
 *
 * PosStore IS part of the main POS bundle and is safe to patch here.
 *
 * WHAT this does:
 * ---------------
 * Before the closing dialog opens we fetch live charity totals via RPC
 * and show a STICKY WARNING notification so the cashier knows:
 *   • How much charity cash was collected this session.
 *   • To remove that amount from the drawer BEFORE counting.
 *
 * The sticky notification stays on screen while the cashier works
 * through the Closing Register dialog — they cannot miss it.
 */
patch(PosStore.prototype, {

    /**
     * Override closePos() to inject the charity reminder BEFORE the
     * closing dialog is shown.
     */
    async closePos() {
        await this._showCharityCloseReminder();
        return super.closePos(...arguments);
    },

    /**
     * Fetch charity totals for the current session via RPC.
     * Displays a sticky warning notification when total > 0.
     */
    async _showCharityCloseReminder() {
        // Skip silently if charity feature is disabled for this POS
        try {
            if (!this.config || !this.config.charity_enabled) {
                return;
            }
        } catch (_) {
            return;
        }

        try {
            const sessionId = this.session?.id;
            if (!sessionId) return;

            const result = await this.env.services.orm.call(
                "pos.session",
                "get_charity_totals",
                [[sessionId]]
            );

            if (!result || !(result.total > 0)) {
                return;
            }

            // Format the amount using POS currency settings
            const currency = this.currency;
            const symbol   = currency?.symbol ?? "₹";
            const dp       = currency?.decimal_places ?? 2;
            const total    = result.total.toFixed(dp);
            const count    = result.count || 0;
            const word     = count === 1 ? "donation" : "donations";

            // Sticky notification — stays visible until cashier dismisses it
            this.env.services.notification.add(
                `❤  Charity collected this session: ${symbol}${total}` +
                ` (${count} ${word}).` +
                `  ⚠ Please remove ${symbol}${total} from the cash drawer` +
                ` before counting cash.`,
                {
                    title:  "Charity Donations — Action Required",
                    type:   "warning",
                    sticky: true,
                }
            );

        } catch (err) {
            // Non-fatal — log and let normal close flow continue
            console.warn(
                "[POS Charity] Could not fetch charity totals for close reminder:",
                err
            );
        }
    },
});