/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {

    async createPartner(vals) {

        const cashCustomer = this.models["res.partner"].find(
            (p) => p.name === "CASH CUSTOMER"
        );

        if (cashCustomer) {
            vals.parent_id = cashCustomer.id;
        }

        return await super.createPartner(vals);
    },

});