/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { SpecialOfferPopup } from "@pos_special_offers/static/src/js/special_offer_popup";

export class SpecialOfferButton extends Component {
    static template = "pos_special_offers.SpecialOfferButton";
    static components = { SpecialOfferPopup };

    setup() {
        this.offerService = useService("special_offer_service");
        this.state = useState({ showPopup: false });
        try { this.pos = useService("pos"); } catch (e) { this.pos = null; }
    }

    get products() {
        try {
            if (!this.pos) return [];
            const m = this.pos.models?.["product.product"];
            if (!m) return [];
            return typeof m.getAll === "function" ? m.getAll()
                : Object.values(m).filter(p => p?.id);
        } catch (e) { return []; }
    }

    get categories() {
        try {
            if (!this.pos) return [];
            const m = this.pos.models?.["pos.category"];
            if (!m) return [];
            return typeof m.getAll === "function" ? m.getAll()
                : Object.values(m).filter(c => c?.id);
        } catch (e) { return []; }
    }

    onClick() { this.state.showPopup = true; }
    closePopup() { this.state.showPopup = false; }
}

// ─────────────────────────────────────────────────────────────────────────────
// Find and patch the Navbar component so it knows about SpecialOfferButton.
//
// OWL resolves component tags (<SpecialOfferButton/>) by looking in the
// parent component's static `components` property at render time.
// So we MUST add SpecialOfferButton to Navbar.components.
//
// We search odoo.loader.modules (a Map) for any module that exports a
// class called "Navbar" - this works regardless of the exact file path.
// ─────────────────────────────────────────────────────────────────────────────
function findAndPatchNavbar() {
    let found = false;
    // odoo.loader.modules is a Map<string, moduleExports>
    for (const [path, mod] of odoo.loader.modules) {
        if (
            path.includes("point_of_sale") &&
            path.toLowerCase().includes("navbar") &&
            mod?.Navbar
        ) {
            try {
                patch(mod.Navbar, {
                    components: {
                        ...mod.Navbar.components,
                        SpecialOfferButton,
                    },
                });
                console.log("[SpecialOffers] ✅ Patched Navbar at path:", path);
                found = true;
                break;
            } catch (e) {
                console.warn("[SpecialOffers] Patch failed for path:", path, e);
            }
        }
    }

    if (!found) {
        // Last resort: scan ALL loaded modules for any export named Navbar
        for (const [path, mod] of odoo.loader.modules) {
            if (mod?.Navbar && path.includes("point_of_sale")) {
                console.log("[SpecialOffers] Found Navbar-like export at:", path, mod.Navbar);
                try {
                    patch(mod.Navbar, {
                        components: {
                            ...mod.Navbar.components,
                            SpecialOfferButton,
                        },
                    });
                    console.log("[SpecialOffers] ✅ Patched via fallback scan:", path);
                    found = true;
                    break;
                } catch (e) {}
            }
        }
    }

    if (!found) {
        console.error(
            "[SpecialOffers] ❌ Could not find Navbar in any module. " +
            "Open browser console and run: " +
            "for(const [k,v] of odoo.loader.modules) { if(k.includes('point_of_sale')) console.log(k); }"
        );
    }
}

findAndPatchNavbar();
