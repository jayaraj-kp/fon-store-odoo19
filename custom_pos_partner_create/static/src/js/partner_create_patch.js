/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PartnerListScreen } from "@point_of_sale/app/screens/partner_list/partner_list";
import { useService } from "@web/core/utils/hooks";
import { onMounted } from "@odoo/owl";

patch(PartnerListScreen.prototype, {
    setup() {
        super.setup(...arguments);
        // Get the dialog service to open backend dialogs
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.action = useService("action");
    },

    /**
     * Override the createPartner method.
     * Instead of opening the POS built-in PartnerEditor,
     * open the backend "Create Contact" form view in a dialog.
     */
    async createPartner() {
        // Open backend res.partner form in dialog mode
        // This triggers the "Create Contact" style wizard (Image 2)
        const result = await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",          // <-- opens as a dialog/modal
            context: {
                default_customer_rank: 1,
                // This context key makes it open in "contact" sub-type mode
                // matching the Create Contact wizard appearance
            },
        });

        // After the dialog closes, refresh the partner list in POS
        // so the newly created partner appears
        if (result) {
            await this.pos.load_new_partners();
            // Optionally auto-select the newly created partner
        }
    },

    /**
     * Override the edit handler so existing partner edits
     * also use the backend form (optional - remove if you only
     * want to affect new creation).
     */
    async editPartner(partner) {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            view_mode: "form",
            views: [[false, "form"]],
            res_id: partner.id,
            target: "new",
        });

        // Refresh partner data after edit
        await this.pos.load_new_partners();
    },
});