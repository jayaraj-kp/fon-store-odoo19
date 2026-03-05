/** @odoo-module **/

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Navbar } from "@point_of_sale/app/navbar/navbar";
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

// Register InvoiceButton as a sub-component of Navbar so OWL
// can resolve <InvoiceButton/> inside the Navbar XML template patch.
patch(Navbar, {
    components: {
        ...Navbar.components,
        InvoiceButton,
    },
});
