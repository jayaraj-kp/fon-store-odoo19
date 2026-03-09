/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CreateContactPopup } from "@pos_cash_customer/js/CreateContactPopup";
import { useService } from "@web/core/utils/hooks";
import { onMounted } from "@odoo/owl";

// Directly import CustomerList - Odoo 19 CE has this path available in the bundle
// even if it doesn't appear as a standalone importable module from outside.
// We use a dynamic workaround via the loader's internal map.
let CustomerList = null;

try {
    odoo.loader.modules.forEach((mod, key) => {
        if (
            !CustomerList &&
            mod &&
            typeof mod === "object" &&
            mod.CustomerList
        ) {
            CustomerList = mod.CustomerList;
        }
    });
} catch (e) {
    // odoo.loader not ready yet - will be patched below via define
}

function doPatch(CL) {
    if (!CL || CL.__cash_patched__) return;
    CL.__cash_patched__ = true;

    patch(CL.prototype, {
        setup() {
            super.setup(...arguments);
            this._cashDialog = useService("dialog");
            onMounted(() => {
                try {
                    const order = this.pos.get_order();
                    if (!order || order.get_partner()) return;
                    const id = this.pos.config.cash_customer_id;
                    if (!id) return;
                    const p = this.pos.models["res.partner"];
                    const found = p && p.find((x) => x.id === id);
                    if (found) order.set_partner(found);
                } catch (e) {
                    console.warn("[pos_cash_customer]", e);
                }
            });
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

if (CustomerList) {
    doPatch(CustomerList);
} else {
    // Hook into the loader: intercept when the CustomerList module is defined
    const _origDefine = odoo.loader.define.bind(odoo.loader);
    odoo.loader.define = function (name, deps, factory) {
        const result = _origDefine(name, deps, factory);
        if (name && name.includes("customer_list")) {
            try {
                const mod = odoo.loader.modules.get(name);
                if (mod && mod.CustomerList) doPatch(mod.CustomerList);
            } catch (e) {}
        }
        return result;
    };
}
