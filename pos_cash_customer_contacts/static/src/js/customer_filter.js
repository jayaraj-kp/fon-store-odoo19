/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";

function getParentId(partner) {
    /** Extract numeric parent_id regardless of format */
    const p = partner.parent_id;
    if (!p) return null;
    if (typeof p === 'number') return p;
    if (typeof p === 'object' && !Array.isArray(p)) return p.id ?? null;
    if (Array.isArray(p)) return p[0] ?? null;
    return null;
}

patch(PartnerList.prototype, {
    setup() {
        super.setup();

        const model = this.pos.models["res.partner"];

        // Find Cash Customer in the model
        const cashCustomer = model.find(
            (p) => p.name === "Cash Customer" && !getParentId(p)
        );

        this._cashCustomerId = cashCustomer ? cashCustomer.id : null;

        console.log("[POS_FILTER] Cash Customer found:", this._cashCustomerId, cashCustomer?.name);

        // Debug ALL partners in model
        model.filter(() => true).forEach(p => {
            console.log("[POS_FILTER] model partner:", p.id, p.name, "parent_id raw:", JSON.stringify(p.parent_id), "-> parsed:", getParentId(p));
        });

        // Set initialPartners
        if (this._cashCustomerId) {
            this.state.initialPartners = model.filter((p) => getParentId(p) === this._cashCustomerId);
        } else {
            this.state.initialPartners = model.filter((p) => !!getParentId(p));
        }

        console.log("[POS_FILTER] initialPartners:", this.state.initialPartners.map(p => p.name));
    },

    getPartners(partners) {
        // Debug what comes in
        if (partners.length > 0) {
            console.log("[POS_FILTER] getPartners() called, sample parent_id:", JSON.stringify(partners[0]?.parent_id), "cashCustomerId:", this._cashCustomerId);
        }

        let filtered;
        if (this._cashCustomerId) {
            filtered = partners.filter((p) => getParentId(p) === this._cashCustomerId);
        } else {
            filtered = partners.filter((p) => !!getParentId(p));
        }

        console.log("[POS_FILTER] getPartners: in=", partners.length, "out=", filtered.length, filtered.map(p => p.name));

        return super.getPartners(filtered);
    },
});
