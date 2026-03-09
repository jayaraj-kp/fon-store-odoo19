/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CustomerList } from "@point_of_sale/app/screens/customer_list/customer_list";
import { CreateContactPopup } from "./CreateContactPopup";

patch(CustomerList.prototype, {
    setup() {
        super.setup(...arguments);
        this._setDefaultCashCustomer();
    },

    _setDefaultCashCustomer() {
        try {
            const order = this.pos.get_order();
            if (!order || order.get_partner()) return;
            const cashCustomerId = this.pos.config.cash_customer_id;
            if (!cashCustomerId) return;
            const partners = this.pos.models["res.partner"];
            if (!partners) return;
            const cashPartner = partners.find((p) => p.id === cashCustomerId);
            if (cashPartner) {
                order.set_partner(cashPartner);
            }
        } catch (e) {
            console.warn("[pos_cash_customer] Could not set default cash customer:", e);
        }
    },

    async createCustomer() {
        const { confirmed, payload } = await this.dialog.add(CreateContactPopup, {
            title: "Create Contact",
        });
        if (confirmed && payload) {
            const order = this.pos.get_order();
            if (order) order.set_partner(payload);
            this.props.close();
        }
    },
});
