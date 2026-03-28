/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ClosePosPopup } from "@point_of_sale/app/screens/close_pos_popup/close_pos_popup";
import { useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

patch(ClosePosPopup.prototype, {
    setup() {
        super.setup(...arguments);

        // Try to get services safely — ClosePosPopup may use env.pos or the service
        try {
            this._charityPos = useService("pos");
        } catch (_) {
            this._charityPos = this.env?.pos || null;
        }

        this.charityClosingState = useState({
            total: 0,
            count: 0,
            loaded: false,
        });

        onMounted(async () => {
            await this._loadCharityTotals();
        });
    },

    async _loadCharityTotals() {
        try {
            const pos = this._charityPos || this.env?.pos;
            if (!pos) return;

            // Only proceed if charity is enabled on this POS config
            if (!pos.config?.charity_enabled) return;

            const sessionId = pos.session?.id;
            if (!sessionId) return;

            // Call the server RPC to get fresh charity totals
            const result = await pos.orm.call(
                "pos.session",
                "get_charity_totals",
                [sessionId],
            );

            if (result && typeof result.total === "number") {
                this.charityClosingState.total = result.total;
                this.charityClosingState.count = result.count || 0;
                this.charityClosingState.loaded = true;
            }
        } catch (e) {
            // Silently fail — charity info is informational, not critical
            console.warn("[CharityClosing] Could not load charity totals:", e);
        }
    },

    /** Expose to template */
    get charityEnabled() {
        const pos = this._charityPos || this.env?.pos;
        return !!(pos?.config?.charity_enabled && this.charityClosingState.loaded && this.charityClosingState.total > 0);
    },

    get charityTotal() {
        return this.charityClosingState.total || 0;
    },

    get charityCount() {
        return this.charityClosingState.count || 0;
    },

    get charityCurrencySymbol() {
        const pos = this._charityPos || this.env?.pos;
        return pos?.currency?.symbol || "₹";
    },
});