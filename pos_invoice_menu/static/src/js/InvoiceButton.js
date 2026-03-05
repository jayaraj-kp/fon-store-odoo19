/** @odoo-module **/

/**
 * POS Invoice Menu — Navbar Button
 *
 * APPROACH: Pure registry-based, zero @point_of_sale/* imports.
 *
 * Instead of patching Navbar (which requires knowing its internal path),
 * we register a "system tray" style component via the pos_widget registry.
 * Odoo 17/18/19 renders all items in registry("pos_widget") inside the POS shell.
 */

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

class InvoiceButton extends Component {
    static template = "pos_invoice_menu.InvoiceButton";

    setup() {
        this.pos = useService("pos_store");
    }

    openInvoiceScreen() {
        this.pos.showScreen("InvoiceListScreen");
    }
}

// Register as a POS widget — Odoo renders these automatically
// in the POS interface without needing Navbar.components patching
registry.category("pos_widget").add(
    "pos_invoice_menu.InvoiceButton",
    { component: InvoiceButton },
    { sequence: 30 }
);
