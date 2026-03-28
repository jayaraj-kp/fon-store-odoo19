/** @odoo-module **/

import { useState, onMounted, Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

// ── CharityClosingSummary component ──────────────────────────────────────────
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
            const result = await pos.orm.call(
                "pos.session", "get_charity_totals", [sessionId]
            );
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

// ── Patch ClosePosPopup via its direct Odoo 19 CE import path ─────────────────
// The error stack shows the class IS called ClosePosPopup — we just need to
// find it. Try all known paths across Odoo 16/17/18/19:
const CLOSE_POPUP_PATHS = [
    "@point_of_sale/app/screens/close_pos_popup/close_pos_popup",
    "@point_of_sale/app/screens/closing_popup/closing_popup",
    "@point_of_sale/app/screens/close_popup/close_popup",
    "@point_of_sale/app/popup/close_pos_popup",
];

async function tryPatchByImport() {
    for (const path of CLOSE_POPUP_PATHS) {
        try {
            // Dynamic import — fails silently if path is wrong
            const mod = await import(/* @vite-ignore */ path);
            const Comp = mod.ClosePosPopup || mod.default;
            if (Comp && typeof Comp === "function") {
                Comp.components = { ...(Comp.components || {}), CharityClosingSummary };
                console.log("[CharityClosing] ✅ Patched via import:", path);
                return true;
            }
        } catch (_) {}
    }
    return false;
}

// ── Fallback: scan __owl__ app globalComponents ───────────────────────────────
function tryPatchViaOwlApps() {
    // In Odoo 19 CE, the OWL App exposes globalComponents which are available
    // to ALL templates in the app — this is the cleanest universal solution.
    const owlLib = window.owl;
    if (!owlLib) return false;

    const apps = owlLib.__apps__;
    if (!apps || !apps.size) return false;

    for (const app of apps) {
        // Register as a global component — available in ALL templates
        app.globalComponents = app.globalComponents || {};
        app.globalComponents.CharityClosingSummary = CharityClosingSummary;
        console.log("[CharityClosing] ✅ Registered as global OWL component");
    }
    return true;
}

// Run immediately and after delays to catch the app after full boot
tryPatchByImport();
[0, 100, 500, 1500].forEach(t => setTimeout(tryPatchViaOwlApps, t));