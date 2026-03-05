/** @odoo-module **/

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { InvoiceListScreen } from "@pos_invoice_menu/js/InvoiceListScreen";

export class InvoiceButton extends Component {
    static template = "pos_invoice_menu.InvoiceButton";
    static components = {};

    setup() {
        this.pos = usePos();
    }

    openInvoiceScreen() {
        this.pos.showScreen("InvoiceListScreen");
    }
}
