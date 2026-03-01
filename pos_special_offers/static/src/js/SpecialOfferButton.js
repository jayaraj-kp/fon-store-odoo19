/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { SpecialOfferPopup } from "@pos_special_offers/js/SpecialOfferPopup";

export class SpecialOfferButton extends Component {
    static template = "pos_special_offers.SpecialOfferButton";
    static components = { SpecialOfferPopup };

    setup() {
        this.pos = usePos();
        this.state = useState({ showPopup: false });
    }

    get products() {
        try {
            const productMap = this.pos.models["product.product"];
            if (productMap && typeof productMap.getAll === "function") {
                return productMap.getAll();
            }
            // Fallback: iterate as object values
            return Object.values(productMap || {}).filter(p => p && p.id);
        } catch (e) {
            return [];
        }
    }

    get categories() {
        try {
            const catMap = this.pos.models["pos.category"];
            if (catMap && typeof catMap.getAll === "function") {
                return catMap.getAll();
            }
            return Object.values(catMap || {}).filter(c => c && c.id);
        } catch (e) {
            return [];
        }
    }

    onClick() {
        this.state.showPopup = true;
    }

    closePopup() {
        this.state.showPopup = false;
    }
}
