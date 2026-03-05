/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CustomerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

/**
 * Patch CustomerList so that when a cash_customer_id is configured,
 * new customers are created as child contacts under the master CASH CUSTOMER
 * partner instead of as standalone partners.
 *
 * Deliberately imports NOTHING from point_of_sale internals beyond
 * CustomerList itself, to avoid broken-path errors across Odoo 19 patch releases.
 */
patch(CustomerList.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.notification = useService("notification");
    },

    async createPartner() {
        const cashCustomerId = this.pos.config.cash_customer_id;

        // No cash customer configured → standard Odoo behaviour
        if (!cashCustomerId) {
            return super.createPartner(...arguments);
        }

        // Resolve master partner name
        let cashCustomerName = "CASH CUSTOMER";
        try {
            const rows = await this.orm.read("res.partner", [cashCustomerId], ["name"]);
            if (rows && rows.length) {
                cashCustomerName = rows[0].name;
            }
        } catch (_e) { /* use default */ }

        // Collect the new customer name via a native browser prompt.
        // This avoids any dependency on POS or web dialog components.
        const customerName = window.prompt(
            `New customer under "${cashCustomerName}"\n\nEnter customer name:`
        );

        if (!customerName || !customerName.trim()) {
            return; // user cancelled
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
                if (this.state && this.state.editModeProps) {
                    this.state.editModeProps.partner = newPartner;
                }
                if (this.props.getPayload) {
                    this.props.getPayload(newPartner);
                }
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