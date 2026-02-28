/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";

patch(PartnerList.prototype, {
    setup() {
        super.setup();

        // Override initialPartners to only show Cash Customer children
        const model = this.pos.models["res.partner"];
        const cashCustomer = model.find(
            (p) => p.name === "Cash Customer" && !p.parent_id
        );

        if (cashCustomer) {
            this._cashCustomerId = cashCustomer.id;
            this.state.initialPartners = model.filter((p) => {
                const parentId = Array.isArray(p.parent_id)
                    ? p.parent_id[0]
                    : p.parent_id?.id ?? p.parent_id;
                return parentId === cashCustomer.id;
            });
        } else {
            this._cashCustomerId = null;
            // Backend already restricted to children — show all that have a parent
            this.state.initialPartners = model.filter((p) => !!p.parent_id);
        }
    },

    getPartners(partners) {
        // First apply our Cash Customer filter on whatever partners are passed in
        const filtered = partners.filter((p) => {
            if (this._cashCustomerId) {
                const parentId = Array.isArray(p.parent_id)
                    ? p.parent_id[0]
                    : p.parent_id?.id ?? p.parent_id;
                return parentId === this._cashCustomerId;
            }
            // fallback: show only contacts (those with a parent)
            return !!p.parent_id;
        });

        // Then apply the normal Odoo search/sort logic on our filtered set
        return super.getPartners(filtered);
    },
});






