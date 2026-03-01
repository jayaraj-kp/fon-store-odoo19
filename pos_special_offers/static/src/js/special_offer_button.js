/** @odoo-module **/
/**
 * IMPORTANT: This file avoids importing from @point_of_sale/app/store/pos_hook
 * or @point_of_sale/app/navbar/navbar directly because those paths vary between
 * Odoo 16/17/18/19 and cause "module not found" crashes.
 *
 * Instead we:
 * 1. Define the component using only @odoo/owl + @web/core (always available)
 * 2. Use odoo.loader to lazily find and patch the Navbar at runtime AFTER
 *    the POS bundle is fully loaded.
 */
import { Component, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { SpecialOfferPopup } from "@pos_special_offers/static/src/js/special_offer_popup";
import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";

export class SpecialOfferButton extends Component {
    static template = "pos_special_offers.SpecialOfferButton";
    static components = { SpecialOfferPopup };

    setup() {
        this.offerService = useService("special_offer_service");
        this.state = useState({ showPopup: false });

        // Try to get pos models - may not be available outside POS context
        try { this.pos = useService("pos"); } catch (e) { this.pos = null; }
    }

    get products() {
        try {
            if (!this.pos) return [];
            const m = this.pos.models?.["product.product"];
            if (!m) return [];
            return typeof m.getAll === "function"
                ? m.getAll()
                : Object.values(m).filter(p => p?.id);
        } catch (e) { return []; }
    }

    get categories() {
        try {
            if (!this.pos) return [];
            const m = this.pos.models?.["pos.category"];
            if (!m) return [];
            return typeof m.getAll === "function"
                ? m.getAll()
                : Object.values(m).filter(c => c?.id);
        } catch (e) { return []; }
    }

    onClick() { this.state.showPopup = true; }
    closePopup() { this.state.showPopup = false; }
}

// ── Runtime Navbar patch ──────────────────────────────────────────────────────
// We look up the Navbar component from the already-loaded module registry
// rather than importing it statically. This works regardless of the exact path.
function patchNavbarSafely() {
    // Try all known Navbar paths across Odoo versions
    const possiblePaths = [
        "@point_of_sale/app/navbar/navbar",
        "@point_of_sale/app/components/navbar/navbar",
        "@point_of_sale/app/screens/navbar/navbar",
    ];

    for (const path of possiblePaths) {
        try {
            const mod = odoo.loader.modules.get(path);
            if (mod && mod.Navbar) {
                patch(mod.Navbar, {
                    components: { ...mod.Navbar.components, SpecialOfferButton },
                });
                console.log("[SpecialOffers] Patched Navbar from:", path);
                return;
            }
        } catch (e) { /* try next */ }
    }
    console.warn("[SpecialOffers] Could not patch Navbar - button may not appear.");
}

// Run after modules are loaded
if (typeof odoo !== "undefined" && odoo.loader) {
    // Hook into the module loaded event if possible
    const origDefine = odoo.loader.define?.bind(odoo.loader);
    if (origDefine) {
        setTimeout(patchNavbarSafely, 0);
    }
}

// Also register in pos_component registry as fallback
registry.category("pos_component").add("SpecialOfferButton", SpecialOfferButton);
