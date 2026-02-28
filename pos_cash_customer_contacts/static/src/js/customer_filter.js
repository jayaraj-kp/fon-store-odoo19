/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";

patch(PartnerList.prototype, {
    setup() {
        super.setup();

        const model = this.pos.models["res.partner"];

        // Find Cash Customer — backend loads it (ID=11) along with its 3 children
        const cashCustomer = model.find(
            (p) => p.name === "Cash Customer" && !p.parent_id
        );

        // Store cash customer ID for use in getPartners()
        this._cashCustomerId = cashCustomer ? cashCustomer.id : null;

        console.log("[pos_cash_customer_contacts] cashCustomer id:", this._cashCustomerId);

        // Set initialPartners to only Cash Customer's children
        if (this._cashCustomerId) {
            this.state.initialPartners = model.filter((p) => {
                const pid = p.parent_id?.id ?? (Array.isArray(p.parent_id) ? p.parent_id[0] : p.parent_id);
                return pid === this._cashCustomerId;
            });
        } else {
            // Fallback: show only contacts that have any parent
            this.state.initialPartners = model.filter((p) => !!p.parent_id);
        }

        console.log("[pos_cash_customer_contacts] initialPartners:", this.state.initialPartners.map(p => p.name));
    },

    getPartners(partners) {
        // Called by the template — filter to only Cash Customer children
        let filtered;
        if (this._cashCustomerId) {
            filtered = partners.filter((p) => {
                const pid = p.parent_id?.id ?? (Array.isArray(p.parent_id) ? p.parent_id[0] : p.parent_id);
                return pid === this._cashCustomerId;
            });
        } else {
            filtered = partners.filter((p) => !!p.parent_id);
        }

        console.log("[pos_cash_customer_contacts] getPartners: in=", partners.length, "out=", filtered.length);

        return super.getPartners(filtered);
    },
});
