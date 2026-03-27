/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

/**
 * POS Charity — Closing Register Reminder (Odoo 19 CE)
 *
 * Patches PosStore.closePos() to show a sticky warning notification
 * before the closing dialog opens, telling the cashier how much
 * charity cash to remove from the drawer before counting.
 *
 * KEY: We access services via pos.env.services (where pos = the live
 * reactive instance from app.env.services.pos) rather than this.env,
 * because this.env is not reliably set on the prototype when the patch
 * runs through the pos_hr override chain.
 */
patch(PosStore.prototype, {

    async closePos() {
        await this._showCharityCloseReminder();
        return super.closePos(...arguments);
    },

    async _showCharityCloseReminder() {
        try {
            // Get the live reactive POS store instance from the OWL app
            const app = [...owl.App.apps][0];
            if (!app) return;

            const pos = app.env.services.pos;
            if (!pos) return;

            // Check charity is enabled
            if (!pos.config?.charity_enabled) return;

            const sessionId = pos.session?.id;
            if (!sessionId) return;

            // Fetch live charity totals from backend
            const orm = pos.env.services.orm;
            const result = await orm.call(
                "pos.session",
                "get_charity_totals",
                [[sessionId]]
            );

            if (!result || !(result.total > 0)) return;

            // Format amount
            const symbol = pos.currency?.symbol ?? "₹";
            const dp     = pos.currency?.decimal_places ?? 2;
            const total  = result.total.toFixed(dp);
            const count  = result.count || 0;
            const word   = count === 1 ? "donation" : "donations";

            // Show sticky notification — stays visible while cashier
            // works through the Closing Register dialog
            pos.env.services.notification.add(
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
            console.warn(
                "[POS Charity] Could not fetch charity totals for close reminder:",
                err
            );
        }
    },
});