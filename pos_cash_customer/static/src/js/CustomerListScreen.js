/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CreateContactPopup } from "@pos_cash_customer/js/CreateContactPopup";
import { useService } from "@web/core/utils/hooks";
import { onMounted } from "@odoo/owl";

// Lazy patch: find CustomerList via the component registry at runtime
// This avoids importing from paths that may not exist in CE builds
function patchCustomerList() {
    try {
        // Access the registry which is always available
        const { registry } = odoo.loader.modules.get("@web/core/registry");
        const components = registry.category("components");
        const CustomerList = components.get("CustomerList");

        if (!CustomerList) {
            console.warn("[pos_cash_customer] CustomerList not in registry, retrying...");
            return false;
        }

        patch(CustomerList.prototype, {
            setup() {
                super.setup(...arguments);
                this._posDialog = useService("dialog");
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
                    console.warn("[pos_cash_customer] set default cash customer error:", e);
                }
            },

            async createCustomer() {
                const result = await new Promise((resolve) => {
                    this._posDialog.add(CreateContactPopup, {
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
        return true;
    } catch (e) {
        console.warn("[pos_cash_customer] patch error:", e);
        return false;
    }
}

// Try immediately, then retry after a short delay if not ready
if (!patchCustomerList()) {
    setTimeout(patchCustomerList, 500);
}
