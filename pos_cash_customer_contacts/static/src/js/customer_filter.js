/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";

patch(PartnerList.prototype, {
    setup() {
        super.setup();

        // Backend loads: Cash Customer + its 3 children + current user
        const allPartners = [...this.pos.models["res.partner"]];

        // Find Cash Customer (has no parent_id, name = "Cash Customer")
        const cashCustomer = allPartners.find(
            (p) => p.name === "Cash Customer" && !p.parent_id
        );

        if (cashCustomer) {
            // Show only direct children of Cash Customer
            this.state.initialPartners = allPartners.filter((p) => {
                const parentId = Array.isArray(p.parent_id)
                    ? p.parent_id[0]
                    : p.parent_id?.id ?? p.parent_id;
                return parentId === cashCustomer.id;
            });
        } else {
            // Fallback: show any partner that has a parent (is a contact)
            this.state.initialPartners = allPartners.filter((p) => !!p.parent_id);
        }
    },
});




