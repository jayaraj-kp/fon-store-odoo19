/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

export class InvoiceButton extends Component {
    static template = "pos_invoice_menu.InvoiceButton";

    setup() {
        // Real service name found from loader inspection
        this.pos = useService("pos");
    }

    openInvoiceScreen() {
        this.pos.showScreen("InvoiceListScreen");
    }
}

// Patch the real Navbar — path confirmed from odoo.loader inspection
const loader = window.odoo?.loader;
const navbarMod = loader?.modules?.get("@point_of_sale/app/components/navbar/navbar");
if (navbarMod?.Navbar) {
    patch(navbarMod.Navbar, {
        components: {
            ...navbarMod.Navbar.components,
            InvoiceButton,
        },
    });
    console.log("[POS Invoice Menu] ✅ Navbar patched successfully");
} else {
    // Fallback: patch after modules finish loading
    Promise.resolve().then(() => {
        const mod = window.odoo?.loader?.modules?.get("@point_of_sale/app/components/navbar/navbar");
        if (mod?.Navbar) {
            patch(mod.Navbar, {
                components: { ...mod.Navbar.components, InvoiceButton },
            });
            console.log("[POS Invoice Menu] ✅ Navbar patched (deferred)");
        } else {
            console.error("[POS Invoice Menu] ❌ Could not find Navbar to patch");
        }
    });
}
