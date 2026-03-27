/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

/**
 * POS Charity — Closing Register Reminder (Odoo 19 CE)
 *
 * Patches PosStore.closePos() to show a sticky warning notification
 * before the closing dialog opens.
 *
 * KEY FIX: Because pos_hr also overrides PosStore, `this` inside the
 * patch may not expose .config / .session directly. We always read
 * the live POS service from this.env.services.pos which is guaranteed
 * to be the fully-initialized reactive store instance.
 */
patch(PosStore.prototype, {

    async closePos() {
        await this._showCharityCloseReminder();
        return super.closePos(...arguments);
    },

    async _showCharityCloseReminder() {
        try {
            // Always use env.services.pos — works even with pos_hr override chain
            const pos = this.env.services.pos;
            if (!pos) return;

            const config = pos.config;
            if (!config || !config.charity_enabled) {
                return;
            }

            const sessionId = pos.session?.id;
            if (!sessionId) return;

            const orm = this.env.services.orm;
            const result = await orm.call(
                "pos.session",
                "get_charity_totals",
                [[sessionId]]
            );

            if (!result || !(result.total > 0)) {
                return;
            }

            const currency = pos.currency;
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