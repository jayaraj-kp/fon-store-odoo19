/** @odoo-module **/
/**
 * Charity Closing Register – Odoo 19 CE
 *
 * APPROACH: Zero xpath, zero template inheritance.
 * We patch ClosePosPopup by locating it through the `lazy_components` or
 * `pos_screens` registry at runtime and overriding its `setup()` to expose
 * charity totals. Then we inject a <CharityClosingSummary/> call directly
 * into the template string before OWL compiles it — patching the raw template
 * text, not the parsed XML tree — so no xpath is needed at all.
 */

import { registry } from "@web/core/registry";
import { useState, onMounted, Component, useRef, onPatched } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

// ─── CharityClosingSummary component ─────────────────────────────────────────
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

// ─── Raw template string injection ───────────────────────────────────────────
// We patch the raw template TEXT of ClosePosPopup before OWL parses it.
// This inserts <CharityClosingSummary/> right before the closing </t> of the
// template, so it appears at the bottom of whatever content already exists.
// We also add it as a component on ClosePosPopup.

function patchClosePosPopupTemplate(app) {
    if (!app?.rawTemplates) return false;
    const key = "point_of_sale.ClosePosPopup";
    const raw = app.rawTemplates[key];
    if (!raw) return false;
    if (typeof raw === "string") {
        if (raw.includes("CharityClosingSummary")) return true; // already patched
        // Insert before the last </t> closing tag of the template
        app.rawTemplates[key] = raw.replace(
            /(<\/t>\s*)$/,
            `<CharityClosingSummary/>\n$1`
        );
        console.log("[CharityClosing] ✅ Patched template string");
        return true;
    }
    // It's a DOM node — patch innerHTML
    if (raw && raw.firstChild) {
        const inner = raw.innerHTML || "";
        if (inner.includes("CharityClosingSummary")) return true;
        raw.innerHTML = inner + "\n<CharityClosingSummary/>";
        console.log("[CharityClosing] ✅ Patched template DOM node");
        return true;
    }
    return false;
}

function patchClosePosPopupClass(ClosePosPopup) {
    if (!ClosePosPopup || ClosePosPopup._charityPatched) return;
    ClosePosPopup._charityPatched = true;
    ClosePosPopup.components = {
        ...(ClosePosPopup.components || {}),
        CharityClosingSummary,
    };
    console.log("[CharityClosing] ✅ Injected CharityClosingSummary into ClosePosPopup.components");
}

function findAndPatch() {
    let patched = false;

    // Search all known registries
    const regNames = ["pos_screens", "lazy_components", "components", "main_components"];
    for (const rName of regNames) {
        try {
            const cat = registry.category(rName);
            for (const [key, Comp] of (cat.getEntries?.() || [])) {
                if (
                    key?.toLowerCase().includes("close") ||
                    Comp?.name?.toLowerCase().includes("close") ||
                    (Comp?.template || "").toLowerCase().includes("closepos")
                ) {
                    patchClosePosPopupClass(Comp);
                    patched = true;
                }
            }
        } catch (_) {}
    }

    // Also patch the raw template in every OWL app
    const owlApps = (
        window.owl?.__apps__ ||
        window.__owl__?.apps ||
        []
    );
    for (const app of owlApps) {
        patchClosePosPopupTemplate(app);
    }

    // Scan DOM for OWL app instances
    for (const el of document.querySelectorAll("[owl-app], #web_client, .o_pos_config")) {
        const app = el.__owl__?.app;
        if (app) patchClosePosPopupTemplate(app);
    }

    return patched;
}

// Run at various times to catch the app after it boots
[0, 200, 600, 1500, 3000].forEach(t => setTimeout(findAndPatch, t));