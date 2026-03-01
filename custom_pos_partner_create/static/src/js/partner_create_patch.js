/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { useService } from "@web/core/utils/hooks";

patch(PartnerList.prototype, {
    setup() {
        super.setup(...arguments);
        this.action = useService("action");
    },

    async editPartner(partner = false) {
        // Only intercept NEW partner creation (partner === false)
        // Let existing partner editing work normally
        if (partner) {
            return await super.editPartner(partner);
        }

        // Open backend Create Contact form as a dialog
        return new Promise((resolve) => {
            this.action.doAction(
                {
                    type: "ir.actions.act_window",
                    res_model: "res.partner",
                    view_mode: "form",
                    views: [[false, "form"]],
                    target: "new",
                    context: {
                        default_customer_rank: 1,
                    },
                },
                {
                    onClose: async () => {
                        // After dialog closes, reload partners so new one appears
                        try {
                            await this.pos.data.callRelated(
                                "res.partner",
                                "get_new_partner",
                                [this.pos.config.id, [], 0]
                            );
                        } catch (e) {
                            console.warn("Partner reload failed:", e);
                        }
                        resolve(null);
                    },
                }
            );
        });
    },
});