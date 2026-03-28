/** @odoo-module **/

import { useState, onMounted, Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { ClosePosPopup } from "@point_of_sale/app/components/popups/closing_popup/closing_popup";

export class CharityClosingSummary extends Component {
    static template = "pos_charity_ledger.CharityClosingSummary";
    static props = {};

    setup() {
        try { this.pos = useService("pos"); } catch (_) { this.pos = this.env?.pos || null; }
        try { this.orm = useService("orm"); } catch (_) { this.orm = null; }
        this.state = useState({ total: 0, count: 0, loaded: false });
        onMounted(async () => { await this._load(); });
    }

    async _load() {
        try {
            const pos = this.pos || this.env?.pos;
            if (!pos?.config?.charity_enabled) return;

            const sessionId = pos.session?.id;
            if (!sessionId) return;

            // Use the orm service directly (useService("orm"))
            // Fall back to pos.orm, pos.env.services.orm, or fetch via rpc
            const orm = this.orm
                || pos.orm
                || pos.env?.services?.orm
                || this.env?.services?.orm;

            let result;
            if (orm?.call) {
                result = await orm.call("pos.session", "get_charity_totals", [sessionId]);
            } else {
                // Last resort: use fetch directly
                const resp = await fetch("/web/dataset/call_kw", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        jsonrpc: "2.0", method: "call", id: 1,
                        params: {
                            model: "pos.session",
                            method: "get_charity_totals",
                            args: [sessionId],
                            kwargs: {},
                        },
                    }),
                });
                const data = await resp.json();
                result = data?.result;
            }

            if (result && typeof result.total === "number" && result.total > 0) {
                this.state.total = result.total;
                this.state.count = result.count || 0;
                this.state.loaded = true;
            }
        } catch (e) {
            console.warn("[CharityClosing] Could not load totals:", e);
        }
    }

    get show()   { return this.state.loaded && this.state.total > 0; }
    get symbol() { return (this.pos || this.env?.pos)?.currency?.symbol || "₹"; }
    get total()  { return this.state.total; }
    get count()  { return this.state.count; }
}

patch(ClosePosPopup, {
    components: {
        ...ClosePosPopup.components,
        CharityClosingSummary,
    },
});

console.log("[CharityClosing] ✅ CharityClosingSummary registered in ClosePosPopup");