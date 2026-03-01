/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { useService } from "@web/core/utils/hooks";

patch(PartnerList.prototype, {
    setup() {
        super.setup(...arguments);
        this.action = useService("action");
        this.orm = useService("orm");
    },

    async editPartner(partner = false) {
        // Only intercept NEW partner creation
        if (partner) {
            return await super.editPartner(partner);
        }

        // Get the custom simple view ID from the database
        let viewId = false;
        try {
            const views = await this.orm.searchRead(
                "ir.ui.view",
                [["name", "=", "res.partner.pos.simple.form"]],
                ["id"],
                { limit: 1 }
            );
            if (views.length > 0) {
                viewId = views[0].id;
            }
        } catch (e) {
            console.warn("Could not find custom view, using default:", e);
        }

        return new Promise((resolve) => {
            this.action.doAction(
                {
                    type: "ir.actions.act_window",
                    res_model: "res.partner",
                    view_mode: "form",
                    views: [[viewId || false, "form"]],
                    target: "new",
                    context: {
                        default_customer_rank: 1,
                    },
                },
                {
                    onClose: async () => {
                        // Reload partners after creation
                        try {
                            await this.pos.data.callRelated(
                                "res.partner",
                                "get_new_partner",
                                [this.pos.config.id, [], 0]
                            );
                        } catch (e) {
                            console.warn("Partner reload error:", e);
                        }
                        resolve(null);
                    },
                }
            );
        });
    },
});