/** @odoo-module **/
/**
 * NOW WE KNOW THE EXACT PATHS from odoo.loader.modules output:
 *   Navbar  → @point_of_sale/app/components/navbar/navbar
 *   usePos  → @point_of_sale/app/hooks/pos_hook
 *
 * We also know the popup module path was wrong - DO NOT import popup here.
 * SpecialOfferPopup is listed as a component in static template only.
 * Instead, we define a self-contained button that renders popup inline via state.
 */
import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { SpecialOfferPopup } from "@pos_special_offers/js/special_offer_popup";

export class SpecialOfferButton extends Component {
    static template = "pos_special_offers.SpecialOfferButton";
    static components = { SpecialOfferPopup };

    setup() {
        this.pos = usePos();
        this.offerService = useService("special_offer_service");
        this.state = useState({ showPopup: false });
    }

    get products() {
        try {
            const m = this.pos.models["product.product"];
            if (!m) return [];
            return typeof m.getAll === "function" ? m.getAll()
                : Object.values(m).filter(p => p?.id);
        } catch (e) { return []; }
    }

    get categories() {
        try {
            const m = this.pos.models["pos.category"];
            if (!m) return [];
            return typeof m.getAll === "function" ? m.getAll()
                : Object.values(m).filter(c => c?.id);
        } catch (e) { return []; }
    }

    onClick() { this.state.showPopup = true; }
    closePopup() { this.state.showPopup = false; }
}

// Register SpecialOfferButton into Navbar.components
// so OWL can resolve <SpecialOfferButton/> inside Navbar's template
patch(Navbar, {
    components: {
        ...Navbar.components,
        SpecialOfferButton,
    },
});
