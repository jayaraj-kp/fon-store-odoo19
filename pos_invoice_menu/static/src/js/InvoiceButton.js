/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

export class InvoiceButton extends Component {
    static template = "pos_invoice_menu.InvoiceButton";
    static props = {};  // Required in Odoo 19 dev mode to silence warning

    setup() {
        this.pos = useService("pos");
        try { this.posUI = useService("pos_ui"); } catch(e) { this.posUI = null; }
    }

    openInvoiceScreen() {
        // Dump all available info to console so we can debug if needed
        const pos = this.pos;
        console.log("[POS Invoice Menu] Button clicked");
        console.log("[POS Invoice Menu] pos keys:", Object.keys(pos));
        console.log("[POS Invoice Menu] pos prototype methods:",
            Object.getOwnPropertyNames(Object.getPrototypeOf(pos))
                .filter(k => typeof pos[k] === "function")
        );

        // Try every known screen navigation pattern across Odoo 17/18/19
        if (typeof pos.showScreen === "function") {
            console.log("[POS Invoice Menu] Using pos.showScreen");
            return pos.showScreen("InvoiceListScreen");
        }
        if (this.posUI && typeof this.posUI.showScreen === "function") {
            console.log("[POS Invoice Menu] Using posUI.showScreen");
            return this.posUI.showScreen("InvoiceListScreen");
        }
        if (pos.ui && typeof pos.ui.showScreen === "function") {
            console.log("[POS Invoice Menu] Using pos.ui.showScreen");
            return pos.ui.showScreen("InvoiceListScreen");
        }
        if (pos.router && typeof pos.router.navigate === "function") {
            console.log("[POS Invoice Menu] Using pos.router.navigate");
            return pos.router.navigate("InvoiceListScreen");
        }
        if (typeof pos.set === "function") {
            console.log("[POS Invoice Menu] Using pos.set selectedScreen");
            return pos.set("selectedScreen", { name: "InvoiceListScreen" });
        }
        // Last resort: look through all OWL apps
        const apps = owl.__apps__ || [];
        for (const app of apps) {
            const posService = app.env?.services?.pos;
            if (posService && typeof posService.showScreen === "function") {
                console.log("[POS Invoice Menu] Found showScreen via owl.__apps__");
                return posService.showScreen("InvoiceListScreen");
            }
        }
        console.error("[POS Invoice Menu] ❌ No showScreen method found anywhere. Please share console output.");
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
