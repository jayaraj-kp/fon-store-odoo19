/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ClosePosPopup } from "@pos_hr/app/components/popups/closing_popup/closing_popup";
import { useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * POS Charity — Closing Register Integration (Odoo 19 CE)
 *
 * We patch pos_hr's ClosePosPopup (which IS in the main POS bundle)
 * to inject charity totals into the closing register dialog.
 *
 * The companion XML (charity_closing_popup.xml) extends the
 * pos_hr closing popup template to render the charity section.
 */
patch(ClosePosPopup.prototype, {

    setup() {
        super.setup(...arguments);

        this.charityState = useState({
            total: 0,
            count: 0,
            loaded: false,
        });

        this.orm = useService("orm");

        onMounted(async () => {
            await this._loadCharityTotals();
        });
    },

    async _loadCharityTotals() {
        try {
            const app = [...owl.App.apps][0];
            if (!app) return;

            const pos = app.env.services.pos;
            if (!pos || !pos.config?.charity_enabled) return;

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
            console.warn("[POS Charity] Could not load charity totals:", e);
            this.charityState.loaded = true;
        }
    },

    get charityData() {
        if (!this.charityState.loaded || this.charityState.total <= 0) {
            return null;
        }
        return {
            total: this.charityState.total,
            count: this.charityState.count,
        };
    },

    get charityAmountFormatted() {
        try {
            const app = [...owl.App.apps][0];
            const pos = app?.env?.services?.pos;
            const symbol = pos?.currency?.symbol ?? "₹";
            const dp = pos?.currency?.decimal_places ?? 2;
            return symbol + (this.charityState.total || 0).toFixed(dp);
        } catch (_) {
            return "₹" + (this.charityState.total || 0).toFixed(2);
        }
    },
});