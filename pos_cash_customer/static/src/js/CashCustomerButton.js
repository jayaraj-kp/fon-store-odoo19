/** @odoo-module **/

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { PartnerListScreen } from "@point_of_sale/app/screens/partner_list/partner_list";
import { patch } from "@web/core/utils/patch";

/**
 * Patch the PartnerListScreen to:
 * 1. Show the CASH CUSTOMER info banner
 * 2. When "Create" is clicked, ensure new customer gets CASH CUSTOMER as parent
 */
patch(PartnerListScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
    },

    /**
     * Returns the master CASH CUSTOMER for display in the template.
     */
    get cashCustomer() {
        return this.pos.getCashCustomer ? this.pos.getCashCustomer() : null;
    },

    /**
     * Override createPartner to inject CASH CUSTOMER as parent
     * before opening the edit form.
     */
    async createPartner() {
        const cashCustomer = this.cashCustomer;
        // Call super — the CreateEditPartner patch will handle the parent prefill
        await super.createPartner(...arguments);
    },
});
