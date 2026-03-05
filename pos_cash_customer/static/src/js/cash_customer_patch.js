/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

patch(PartnerList.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.notification = useService("notification");
    },

    /**
     * In Odoo 19, the Create button calls editPartner(false) — not createPartner().
     * We intercept here: if p=false (new partner) AND cash_customer_id is set,
     * we show our prompt instead of the standard Edit Partner dialog.
     */
    async editPartner(p = false) {
        const cashCustomerId = this.pos.config.cash_customer_id;

        // If editing an EXISTING partner, or no cash customer configured → default behaviour
        if (p || !cashCustomerId) {
            return super.editPartner(p);
        }

        // Resolve master partner name
        let cashCustomerName = "CASH CUSTOMER";
        try {
            const rows = await this.orm.read("res.partner", [cashCustomerId], ["name"]);
            if (rows && rows.length) {
                cashCustomerName = rows[0].name;
            }
        } catch (_e) { /* use default */ }

        // Collect new customer name
        const customerName = window.prompt(
            `New customer under "${cashCustomerName}"\n\nEnter customer name:`
        );

        if (!customerName || !customerName.trim()) {
            return;
        }

        try {
            const newPartnerId = await this.orm.create("res.partner", [
                {
                    name: customerName.trim(),
                    parent_id: cashCustomerId,
                    type: "contact",
                    customer_rank: 1,
                },
            ]);

            await this.pos.loadNewPartner(newPartnerId);

            const newPartner = this.pos.models["res.partner"].find(
                (p) => p.id === newPartnerId
            );

            if (newPartner) {
                this.clickPartner(newPartner);
            }

            this.notification.add(
                _t("'%s' created under %s", customerName.trim(), cashCustomerName),
                { type: "success" }
            );
        } catch (err) {
            this.notification.add(
                _t("Failed to create customer: %s", err.message),
                { type: "danger" }
            );
        }
    },
});