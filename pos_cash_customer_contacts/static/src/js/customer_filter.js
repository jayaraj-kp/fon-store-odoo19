/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CustomerList } from "@point_of_sale/app/screens/partner_list/partner_list";

/**
 * Patch the POS CustomerList screen to filter and display
 * only contacts (children) of the 'Cash Customer' partner.
 */
patch(CustomerList.prototype, {

    /**
     * Returns filtered partners: only those whose parent
     * is named 'Cash Customer'.
     */
    get partners() {
        const allPartners = super.partners;

        // Find the Cash Customer parent partner
        const cashCustomer = Object.values(this.pos.db.partner_by_id || {}).find(
            (p) => p.name === "Cash Customer" && !p.parent_id
        );

        if (!cashCustomer) {
            // If Cash Customer not found, show nothing to avoid confusion
            console.warn(
                "[pos_cash_customer_contacts] 'Cash Customer' not found in POS partner list."
            );
            return [];
        }

        // Filter only contacts whose parent_id matches Cash Customer
        return allPartners.filter(
            (partner) => partner.parent_id && partner.parent_id[0] === cashCustomer.id
        );
    },
});