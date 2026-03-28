/** @odoo-module **/

/**
 * Charity Closing Register Patch – Odoo 19 CE compatible
 *
 * We do NOT import ClosePosPopup directly (its path differs per version).
 * Instead we export CharityClosingSummary as a standalone component and
 * let charity_closing_popup.xml inherit "point_of_sale.ClosePosPopup"
 * (the TEMPLATE name, not the JS module) and inject our component there.
 *
 * The component is also added to the global components registry so OWL
 * can resolve it when the template uses <CharityClosingSummary/>.
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

// Make it available globally for OWL template resolution
registry.category("pos_charity_closing").add("CharityClosingSummary", CharityClosingSummary);

// Also inject into owl __apps__ global components after boot
// so the t-inherit template can find <CharityClosingSummary/>
function injectGlobalComponent() {
    try {
        // Odoo 19 CE: owl.App instances expose globalComponents
        if (window.__owl_app__ && window.__owl_app__.globalComponents) {
            window.__owl_app__.globalComponents.CharityClosingSummary = CharityClosingSummary;
            return true;
        }
        // Try the odoo global namespace
        if (window.owl?.apps) {
            for (const app of window.owl.apps) {
                app.globalComponents = app.globalComponents || {};
                app.globalComponents.CharityClosingSummary = CharityClosingSummary;
            }
            return true;
        }
    } catch (_) {}
    return false;
}

// Retry a few times — apps may not be ready at module load time
[100, 500, 1500, 3000].forEach(delay =>
    setTimeout(injectGlobalComponent, delay)
);