/** @odoo-module **/

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { SpecialOfferPopup } from "./SpecialOfferPopup";

export class SpecialOfferButton extends Component {
    static template = "pos_special_offers.SpecialOfferButton";
    static components = { SpecialOfferPopup };

    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
    }

    onClick() {
        // Get products and categories from POS loaded data
        const products = Object.values(this.pos.models["product.product"] || {});
        const categories = Object.values(this.pos.models["pos.category"] || {});

        this.dialog.add(SpecialOfferPopup, {
            products: Array.isArray(products) ? products : [],
            categories: Array.isArray(categories) ? categories : [],
        });
    }
}

// Register button in POS top bar
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";

patch(ProductScreen, {
    components: {
        ...ProductScreen.components,
        SpecialOfferButton,
    },
});
