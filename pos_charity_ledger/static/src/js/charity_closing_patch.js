/** @odoo-module **/

/**
 * Charity Closing Register – Pure JS patch, NO template inheritance.
 *
 * Root cause of all previous errors:
 *  - Importing ClosePosPopup by path fails because the path differs per version.
 *  - xpath template inheritance fails because the CSS class names differ per version.
 *
 * This file solves both by:
 *  1. Defining CharityClosingSummary as a standalone OWL component with its OWN template.
 *  2. Using the odoo `lazy_components` / `components` registry to locate ClosePosPopup
 *     at RUNTIME (after all modules are loaded) and injecting CharityClosingSummary
 *     into its `components` map so the template can use <CharityClosingSummary/>.
 *  3. Using `t-inherit` on ClosePosPopup's TEMPLATE (not the JS module) with a
 *     xpath that targets `//div` (the first div, which always exists) — but only
 *     PREPENDING our component call, not relying on any specific class.
 */

import { registry } from "@web/core/registry";
import { useState, onMounted, Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

// ─────────────────────────────────────────────────────────────────────────────
// CharityClosingSummary component
// ─────────────────────────────────────────────────────────────────────────────
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

// ─────────────────────────────────────────────────────────────────────────────
// Runtime injection — find ClosePosPopup in any registry and add our component
// ─────────────────────────────────────────────────────────────────────────────
function injectIntoClosingPopup() {
    const categoriesToSearch = [
        "pos_screens", "lazy_components", "components",
        "actions", "views", "main_components",
    ];
    for (const catName of categoriesToSearch) {
        try {
            const cat = registry.category(catName);
            const entries = cat.getEntries?.() || [];
            for (const [key, Comp] of entries) {
                const isClosing =
                    key?.toLowerCase().includes("close") ||
                    Comp?.name?.toLowerCase().includes("close") ||
                    Comp?.template?.toLowerCase().includes("close");
                if (isClosing && Comp && typeof Comp === "function") {
                    Comp.components = { ...(Comp.components || {}), CharityClosingSummary };
                    console.log("[CharityClosing] ✅ Injected into", key, "from registry", catName);
                }
            }
        } catch (_) {}
    }
}

// Run after all modules have loaded
setTimeout(injectIntoClosingPopup, 0);