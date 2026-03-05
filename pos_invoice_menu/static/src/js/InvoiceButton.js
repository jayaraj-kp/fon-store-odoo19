/** @odoo-module **/

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Chrome } from "@point_of_sale/app/pos_app";
import { patch } from "@web/core/utils/patch";

export class InvoiceButton extends Component {
    static template = "pos_invoice_menu.InvoiceButton";

    setup() {
        this.pos = usePos();
    }

    openInvoiceScreen() {
        this.pos.showScreen("InvoiceListScreen");
    }
}

// Patch Chrome to include InvoiceButton as a sub-component
// so the XML template can reference it by name.
patch(Chrome, {
    components: {
        ...Chrome.components,
        InvoiceButton,
    },
});
