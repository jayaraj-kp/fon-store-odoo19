/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CreateContactPopup } from "@pos_cash_customer/js/CreateContactPopup";
import { useService } from "@web/core/utils/hooks";
import { onMounted } from "@odoo/owl";

// Use Odoo 19's module loader to find CustomerList at runtime
// after all modules are loaded
function applyPatch() {
    const modules = odoo.__DEBUG__.services || {};

    // Walk through loader module map to find CustomerList
    let CustomerList = null;

    try {
        // Odoo 19 stores loaded modules in odoo.loader.modules (a Map)
        odoo.loader.modules.forEach((mod, key) => {
            if (!CustomerList && mod && typeof mod === "object") {
                if (mod.CustomerList && mod.CustomerList.prototype) {
                    CustomerList = mod.CustomerList;
                    console.log("[pos_cash_customer] Found CustomerList in:", key);
                }
            }
        });
    } catch (e) {
        console.warn("[pos_cash_customer] loader scan failed:", e);
    }

    if (!CustomerList) {
        console.error("[pos_cash_customer] ❌ CustomerList not found - cannot patch");
        return;
    }

    patch(CustomerList.prototype, {
        setup() {
            super.setup(...arguments);
            this._cashDialog = useService("dialog");
            onMounted(() => this._setDefaultCashCustomer());
        },

        _setDefaultCashCustomer() {
            try {
                const order = this.pos.get_order();
                if (!order || order.get_partner()) return;
                const cashCustomerId = this.pos.config.cash_customer_id;
                if (!cashCustomerId) return;
                const partners = this.pos.models["res.partner"];
                const cashPartner = partners && partners.find((p) => p.id === cashCustomerId);
                if (cashPartner) order.set_partner(cashPartner);
            } catch (e) {
                console.warn("[pos_cash_customer] set default:", e);
            }
        },

        async createCustomer() {
            const result = await new Promise((resolve) => {
                this._cashDialog.add(CreateContactPopup, {
                    title: "Create Contact",
                    close: resolve,
                });
            });
            if (result && result.confirmed && result.payload) {
                const order = this.pos.get_order();
                if (order) order.set_partner(result.payload);
                this.props.close();
            }
        },
    });

    console.log("[pos_cash_customer] ✅ CustomerList patched");
}

// Run after all modules are defined
applyPatch();
