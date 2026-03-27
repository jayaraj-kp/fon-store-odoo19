/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

/**
 * POS Charity — Closing Register Reminder  (Odoo 19 CE)
 *
 * Patches PosStore.closePos() to show a sticky warning notification
 * before the closing dialog opens, telling the cashier how much
 * charity cash to remove from the drawer before counting.
 *
 * Correct import path in Odoo 19 CE:
 *   @point_of_sale/app/services/pos_store   ✓
 *   @point_of_sale/app/store/pos_store      ✗  (old path, causes error)
 */
patch(PosStore.prototype, {

    async closePos() {
        await this._showCharityCloseReminder();
        return super.closePos(...arguments);
    },

    async _showCharityCloseReminder() {
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

            const currency = this.currency;
            const symbol   = currency?.symbol ?? "₹";
            const dp       = currency?.decimal_places ?? 2;
            const total    = result.total.toFixed(dp);
            const count    = result.count || 0;
            const word     = count === 1 ? "donation" : "donations";

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
            console.warn(
                "[POS Charity] Could not fetch charity totals for close reminder:",
                err
            );
        }
    },
});