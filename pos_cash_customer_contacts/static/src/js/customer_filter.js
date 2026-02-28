/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";

/**
 * Patch PartnerList to filter initialPartners to only show
 * contacts (children) of the 'Cash Customer' partner.
 *
 * The backend already restricts which partners are loaded via
 * _load_pos_data_domain and get_new_partner overrides.
 * This patch ensures the in-memory JS model is also filtered
 * in case stale data exists from a previous session.
 */
patch(PartnerList.prototype, {
    setup() {
        super.setup();

        // Find the Cash Customer partner in the loaded model
        const allPartners = this.pos.models["res.partner"].getAll
            ? this.pos.models["res.partner"].getAll()
            : Object.values(this.pos.models["res.partner"].records || {});

        const cashCustomer = allPartners.find(
            (p) => p.name === "Cash Customer" && !p.parent_id
        );

        if (cashCustomer) {
            // Override initialPartners to only show Cash Customer's children
            this.state.initialPartners = allPartners.filter((p) => {
                const parentId = Array.isArray(p.parent_id)
                    ? p.parent_id[0]
                    : p.parent_id?.id ?? p.parent_id;
                return parentId === cashCustomer.id;
            });
        } else {
            // Cash Customer not found — show empty list (backend filter is active)
            this.state.initialPartners = [];
        }
    },
});


