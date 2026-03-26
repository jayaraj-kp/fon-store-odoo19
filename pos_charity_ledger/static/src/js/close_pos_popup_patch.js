/** @odoo-module **/

/**
 * Patches ClosePosPopup (Odoo 19 CE) to display the accumulated session
 * charity donation total in the Close Register screen.
 *
 * IMPORTANT: We do NOT call add_charity_pending_amount here.
 * pos_order.py already accumulates the total server-side each time an
 * order with a charity donation is synced. The Python override of
 * action_pos_session_closing_control() reads charity_pending_amount
 * and posts it to the ledger on close.
 *
 * This patch is DISPLAY-ONLY. The template reads pos._sessionCharityTotal,
 * an in-memory running total maintained by charity_button.js.
 */

import { patch } from "@web/core/utils/patch";
import { ClosePosPopup } from "@point_of_sale/app/components/popups/closing_popup/closing_popup";

patch(ClosePosPopup.prototype, {
    /** Total charity collected this session (in-memory, set by charity_button.js). */
    get sessionCharityTotal() {
        const total = (this.pos && this.pos._sessionCharityTotal) || 0;
        return parseFloat(total.toFixed(2));
    },

    get currencySymbol() {
        return this.pos?.currency?.symbol || "₹";
    },

    get charityEnabled() {
        return !!(this.pos?.config?.charity_enabled && this.pos?.config?.charity_account_id);
    },
});
