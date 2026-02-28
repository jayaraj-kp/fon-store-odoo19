/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";

patch(PartnerList.prototype, {
    setup() {
        super.setup();

        // In Odoo 19, this.pos.models["res.partner"] is NOT a plain array.
        // It has a .filter() method — use it directly, same as Odoo core does.
        const model = this.pos.models["res.partner"];

        // Find Cash Customer (loaded by backend, has no parent_id)
        const cashCustomer = model.find(
            (p) => p.name === "Cash Customer" && !p.parent_id
        );

        if (cashCustomer) {
            this.state.initialPartners = model.filter((p) => {
                const parentId = Array.isArray(p.parent_id)
                    ? p.parent_id[0]
                    : p.parent_id?.id ?? p.parent_id;
                return parentId === cashCustomer.id;
            });
        } else {
            // Fallback: show only partners that have a parent (are child contacts)
            this.state.initialPartners = model.filter((p) => !!p.parent_id);
        }
    },
});





