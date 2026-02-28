/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";

patch(PartnerList.prototype, {
    setup() {
        super.setup();

        const model = this.pos.models["res.partner"];

        // DEBUG: understand the model structure
        console.log("=== POS CASH CUSTOMER DEBUG ===");
        console.log("model type:", typeof model);
        console.log("model constructor:", model?.constructor?.name);
        console.log("model keys:", Object.keys(model || {}).slice(0, 20));
        console.log("has .filter:", typeof model?.filter);
        console.log("has .find:", typeof model?.find);
        console.log("has .getAll:", typeof model?.getAll);
        console.log("has .records:", typeof model?.records);
        console.log("has Symbol.iterator:", typeof model?.[Symbol.iterator]);

        // Try different ways to get all partners
        let allPartners = [];
        if (typeof model?.getAll === 'function') {
            allPartners = model.getAll();
            console.log("used getAll(), count:", allPartners.length);
        } else if (typeof model?.filter === 'function') {
            allPartners = model.filter(() => true);
            console.log("used filter(true), count:", allPartners.length);
        } else if (model?.records) {
            allPartners = Object.values(model.records);
            console.log("used .records, count:", allPartners.length);
        }

        console.log("all partners:", allPartners.map(p => ({
            id: p.id,
            name: p.name,
            parent_id: p.parent_id,
            parent_name: p.parent_name,
        })));

        console.log("state.initialPartners count:", this.state.initialPartners?.length);
        console.log("state.initialPartners:", this.state.initialPartners?.map(p => ({
            id: p.id, name: p.name, parent_id: p.parent_id
        })));
        console.log("=== END DEBUG ===");
    },

    getPartners(partners) {
        console.log("[pos_cash_customer_contacts] getPartners called with:", partners.length, "partners");
        console.log("[pos_cash_customer_contacts] partners:", partners.map(p => ({id: p.id, name: p.name, parent_id: p.parent_id})));
        return super.getPartners(partners);
    },
});







