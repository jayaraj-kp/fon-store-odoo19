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

    async editPartner(p = false) {
        // Resolve cash_customer_id — may be an int, a Many2one tuple [id, name], or a record object
        const raw = this.pos.config.cash_customer_id;
        const cashCustomerId = Array.isArray(raw) ? raw[0] : (raw?.id || raw || 0);

        // If editing an existing partner, or no cash customer configured → default behaviour
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

        // Collect new customer name via native prompt
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