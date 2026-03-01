/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { SpecialOfferPopup } from "@pos_special_offers/static/src/js/SpecialOfferPopup";

export class SpecialOfferButton extends Component {
    static template = "pos_special_offers.SpecialOfferButton";
    static components = { SpecialOfferPopup };

    setup() {
        this.pos = usePos();
        this.state = useState({ showPopup: false });
    }

    get products() {
        try {
            const all = this.pos.models["product.product"];
            if (!all) return [];
            if (typeof all.getAll === "function") return all.getAll();
            return Object.values(all).filter(p => p && p.id);
        } catch (e) { return []; }
    }

    get categories() {
        try {
            const all = this.pos.models["pos.category"];
            if (!all) return [];
            if (typeof all.getAll === "function") return all.getAll();
            return Object.values(all).filter(c => c && c.id);
        } catch (e) { return []; }
    }

    onClick() { this.state.showPopup = true; }
    closePopup() { this.state.showPopup = false; }
}

// Register SpecialOfferButton as a known component inside Navbar
patch(Navbar, {
    components: {
        ...Navbar.components,
        SpecialOfferButton,
    },
});
