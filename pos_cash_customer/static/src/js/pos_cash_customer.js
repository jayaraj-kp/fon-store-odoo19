/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CustomerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { PartnerDetailsEdit } from "@point_of_sale/app/screens/partner_list/partner_editor/partner_editor";
import { useService } from "@web/core/utils/hooks";
import { useState, onMounted } from "@odoo/owl";

// ── Patch CustomerList screen ──────────────────────────────────────────────
patch(CustomerList.prototype, {
    setup() {
        super.setup(...arguments);
        this.cashCustomerId = null;
        this._loadCashCustomerId();
    },

    async _loadCashCustomerId() {
        try {
            const result = await this.orm.call(
                "pos.session",
                "get_cash_customer_info",
                []
            );
            this.cashCustomerId = result.id;
            // Store on POS config for access elsewhere
            this.pos.cashCustomerId = result.id;
            this.pos.cashCustomerName = result.name;
        } catch (e) {
            console.warn("[POS Cash Customer] Could not load CASH CUSTOMER id", e);
        }
    },

    /**
     * Override: when saving a new customer from POS,
     * always attach them under the CASH CUSTOMER parent.
     */
    async saveChanges(processedChanges) {
        if (!processedChanges.id) {
            // New customer — inject parent_id = CASH CUSTOMER
            if (this.cashCustomerId) {
                processedChanges.parent_id = this.cashCustomerId;
                processedChanges.is_pos_walk_in = true;
            }
        }
        return super.saveChanges(processedChanges);
    },
});


// ── Patch PartnerDetailsEdit (the create/edit form) ────────────────────────
patch(PartnerDetailsEdit.prototype, {
    setup() {
        super.setup(...arguments);
        // Expose cash customer context to the template
        this.cashCustomerName = this.pos?.cashCustomerName || "CASH CUSTOMER";
        this.isNewCustomer = !this.props.partner?.id;
    },
});
