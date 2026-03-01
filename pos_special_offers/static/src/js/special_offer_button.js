/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { SpecialOfferPopup } from "@pos_special_offers/js/special_offer_popup";

export class SpecialOfferButton extends Component {
    static template = "pos_special_offers.SpecialOfferButton";
    static components = { SpecialOfferPopup };
    static props = {};  // Fix: "does not have a static props description"

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

patch(Navbar, {
    components: {
        ...Navbar.components,
        SpecialOfferButton,
    },
});
