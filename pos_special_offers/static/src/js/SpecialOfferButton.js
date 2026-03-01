/** @odoo-module **/

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { SpecialOfferPopup } from "./SpecialOfferPopup";

/**
 * SpecialOfferButton
 * Renders a "🎁 Offers" button in the POS top menu bar.
 * On click, opens the SpecialOfferPopup dialog.
 */
export class SpecialOfferButton extends Component {
    static template = "pos_special_offers.SpecialOfferButton";
    static components = {};

    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
    }

    get products() {
        // All loaded products available in POS
        try {
            return Object.values(this.pos.db.product_by_id || {});
        } catch {
            return [];
        }
    }

    get categories() {
        // All POS categories
        try {
            return Object.values(this.pos.db.category_by_id || {});
        } catch {
            return [];
        }
    }

    openPopup() {
        this.dialog.add(SpecialOfferPopup, {
            products: this.products,
            categories: this.categories,
        });
    }
}

// ─── Register the button in the POS top bar ──────────────────────────────────
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";

patch(ProductScreen, {
    components: {
        ...ProductScreen.components,
        SpecialOfferButton,
    },
});

// We also need to patch the ProductScreen template to include our button.
// The cleanest way without overriding the full template is to use the
// extraActions registry if available, or extend the headerButtons section.
// For Odoo 17/19, we patch via component registry:
import { registry } from "@web/core/registry";

registry.category("pos_top_bar_actions").add("SpecialOfferButton", {
    component: SpecialOfferButton,
    condition: (pos) => true,
});
