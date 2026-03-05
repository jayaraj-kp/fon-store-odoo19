/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

export class InvoiceButton extends Component {
    static template = "pos_invoice_menu.InvoiceButton";
    static props = {};

    setup() {
        this.pos = useService("pos");
    }

    openInvoiceScreen() {
        // pos.navigate() is the correct method in this Odoo 19 build
        this.pos.navigate("InvoiceListScreen");
    }
}

Promise.resolve().then(() => {
    const mod = window.odoo?.loader?.modules?.get(
        "@point_of_sale/app/components/navbar/navbar"
    );
    if (mod?.Navbar) {
        patch(mod.Navbar, {
            components: { ...mod.Navbar.components, InvoiceButton },
        });
    }
});
