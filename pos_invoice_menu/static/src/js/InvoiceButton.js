/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

export class InvoiceButton extends Component {
    static template = "pos_invoice_menu.InvoiceButton";

    setup() {
        this.pos = useService("pos");
        // In Odoo 19, screen navigation moved to a separate service
        // Try to get it — falls back gracefully if not available
        try { this.ui = useService("pos_ui"); } catch(e) { this.ui = null; }
    }

    openInvoiceScreen() {
        // Method 1: Odoo 17 standard
        if (typeof this.pos.showScreen === "function") {
            return this.pos.showScreen("InvoiceListScreen");
        }
        // Method 2: Odoo 19 — ui service
        if (this.ui && typeof this.ui.showScreen === "function") {
            return this.ui.showScreen("InvoiceListScreen");
        }
        // Method 3: via env directly
        if (typeof this.env.pos?.showScreen === "function") {
            return this.env.pos.showScreen("InvoiceListScreen");
        }
        // Method 4: pos.mainScreen setter (Odoo 17 alternative)
        if ("mainScreen" in this.pos) {
            this.pos.mainScreen = { name: "InvoiceListScreen", component: null };
            return;
        }
        // Debug: log all available functions to console
        console.error(
            "[POS Invoice Menu] showScreen not found. Available pos methods:",
            Object.getOwnPropertyNames(Object.getPrototypeOf(this.pos))
                .filter(k => typeof this.pos[k] === "function"),
            "\nAvailable pos keys:",
            Object.keys(this.pos).slice(0, 30)
        );
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
        console.log("[POS Invoice Menu] ✅ Navbar patched");
    }
});
