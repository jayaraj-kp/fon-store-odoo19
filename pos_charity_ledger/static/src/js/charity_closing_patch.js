/** @odoo-module **/
/**
 * Charity Closing Register – Odoo 19 CE
 *
 * Defines CharityClosingSummary component and injects it into
 * ClosePosPopup.components so the t-inherit XML can call <CharityClosingSummary/>.
 *
 * The xpath in charity_closing_popup.xml targets:
 *   //div[hasclass('payment-methods-overview')]
 * which is confirmed present in the actual DOM.
 */

import { registry } from "@web/core/registry";
import { useState, onMounted, Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class CharityClosingSummary extends Component {
    static template = "pos_charity_ledger.CharityClosingSummary";
    static props = {};

    setup() {
        try { this.pos = useService("pos"); } catch (_) { this.pos = this.env?.pos || null; }
        this.state = useState({ total: 0, count: 0, loaded: false });
        onMounted(async () => { await this._load(); });
    }

    async _load() {
        try {
            const pos = this.pos || this.env?.pos;
            if (!pos?.config?.charity_enabled) return;
            const sessionId = pos.session?.id;
            if (!sessionId) return;
            const result = await pos.orm.call("pos.session", "get_charity_totals", [sessionId]);
            if (result && typeof result.total === "number" && result.total > 0) {
                this.state.total = result.total;
                this.state.count = result.count || 0;
                this.state.loaded = true;
            }
        } catch (e) {
            console.warn("[CharityClosing] Could not load totals:", e);
        }
    }

    get show() { return this.state.loaded && this.state.total > 0; }
    get symbol() { return (this.pos || this.env?.pos)?.currency?.symbol || "₹"; }
    get total() { return this.state.total; }
    get count() { return this.state.count; }
}

// ── Inject into ClosePosPopup.components via registry scan ───────────────────
function injectComponent() {
    const regNames = ["pos_screens", "lazy_components", "components", "main_components"];
    for (const rName of regNames) {
        try {
            for (const [key, Comp] of (registry.category(rName).getEntries?.() || [])) {
                if (
                    key?.toLowerCase().includes("close") ||
                    Comp?.name?.toLowerCase().includes("close")
                ) {
                    if (!Comp._charityPatched) {
                        Comp._charityPatched = true;
                        Comp.components = { ...(Comp.components || {}), CharityClosingSummary };
                        console.log("[CharityClosing] ✅ Injected into", key);
                    }
                }
            }
        } catch (_) {}
    }
}

setTimeout(injectComponent, 0);