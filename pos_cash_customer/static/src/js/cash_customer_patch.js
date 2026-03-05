/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CustomerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { EditPartner } from "@point_of_sale/app/screens/partner_list/edit_partner/edit_partner";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

/**
 * Patch the CustomerList component to intercept the "Create" button click.
 *
 * When a cash_customer_id is configured in POS settings, new customers are
 * created as contacts under that master partner instead of as standalone partners.
 */
patch(CustomerList.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
    },

    async createPartner() {
        const cashCustomerId = this.pos.config.cash_customer_id;

        // No cash customer configured → standard Odoo behaviour
        if (!cashCustomerId) {
            return super.createPartner(...arguments);
        }

        // Fetch the cash customer name for display purposes
        let cashCustomerName = "CASH CUSTOMER";
        try {
            const partners = await this.orm.read(
                "res.partner",
                [cashCustomerId],
                ["name"]
            );
            if (partners && partners.length) {
                cashCustomerName = partners[0].name;
            }
        } catch (_e) {
            // ignore – use default label
        }

        // Open the EditPartner dialog pre-filled with parent_id = cashCustomerId.
        // EditPartner is imported statically above (no dynamic loader needed in Odoo 19).
        this.dialog.add(EditPartner, {
            partner: {
                parent_id: [cashCustomerId, cashCustomerName],
                type: "contact",
            },
            title: _t("New Customer (under %s)", cashCustomerName),
            save: async (processedChanges) => {
                // Always enforce the parent link
                processedChanges.parent_id = cashCustomerId;

                const newPartnerId = await this.orm.create(
                    "res.partner",
                    [processedChanges]
                );

                await this.pos.loadNewPartner(newPartnerId);

                const newPartner = this.pos.models["res.partner"].find(
                    (p) => p.id === newPartnerId
                );

                if (newPartner) {
                    this.state.editModeProps.partner = newPartner;
                }

                this.notification.add(
                    _t("Customer created under %s", cashCustomerName),
                    { type: "success" }
                );

                if (this.props.getPayload) {
                    this.props.getPayload(newPartner);
                }
            },
        });
    },
});