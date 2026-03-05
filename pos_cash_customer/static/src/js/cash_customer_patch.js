/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CustomerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

/**
 * Patch the CustomerList component to intercept the "Create" button click.
 *
 * Logic:
 *  1. Read cash_customer_id from POS config.
 *  2. If NOT set  → open the normal full partner form (standard Odoo behaviour).
 *  3. If SET      → open the "Create Contact" dialog pre-filled with parent_id = cash_customer_id.
 *
 * The patch overrides `createPartner` which is the method called when the
 * "Create" button is clicked in the partner/customer list screen.
 */
patch(CustomerList.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
    },

    /**
     * Called when "Create" button is clicked in the customer chooser.
     * We override this to redirect to the cash-customer contact creation flow.
     */
    async createPartner() {
        const cashCustomerId = this.pos.config.cash_customer_id;

        // If no cash customer is configured, fall back to default behaviour
        if (!cashCustomerId) {
            return super.createPartner(...arguments);
        }

        // Fetch the cash customer partner name for display
        let cashCustomerName = "CASH CUSTOMER";
        try {
            const partners = await this.orm.read(
                "res.partner",
                [cashCustomerId],
                ["name"],
            );
            if (partners && partners.length) {
                cashCustomerName = partners[0].name;
            }
        } catch (_e) {
            // ignore – use default name
        }

        // Open the EditPartner dialog but with parent_id pre-set to cashCustomerId
        // This mimics clicking "Add Contact" under the CASH CUSTOMER record.
        const { EditPartner } = await odoo.loader.modules.get(
            "@point_of_sale/app/screens/partner_list/edit_partner/edit_partner"
        ) || {};

        if (!EditPartner) {
            // Fallback: open via RPC with parent_id context
            return this._createContactFallback(cashCustomerId, cashCustomerName);
        }

        this.dialog.add(EditPartner, {
            partner: {
                // Pre-fill parent_id so the contact is linked to CASH CUSTOMER
                parent_id: [cashCustomerId, cashCustomerName],
                type: "contact",
            },
            title: _t("New Customer (under %s)", cashCustomerName),
            save: async (processedChanges) => {
                // Ensure parent_id is always set to cash customer
                processedChanges.parent_id = cashCustomerId;
                const { id: newPartnerId } = await this.orm.create(
                    "res.partner",
                    [processedChanges]
                );
                // Load new partner and select it
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
                // Trigger partner selection
                this.props.getPayload && this.props.getPayload(newPartner);
            },
        });
    },

    /**
     * Fallback method: creates a partner via ORM with parent_id = cashCustomerId,
     * used when the EditPartner component is not accessible via the module loader.
     */
    async _createContactFallback(cashCustomerId, cashCustomerName) {
        const contactName = await new Promise((resolve) => {
            // Simple prompt as last resort
            const name = window.prompt(
                `Enter customer name (will be added under ${cashCustomerName}):`
            );
            resolve(name);
        });

        if (!contactName || !contactName.trim()) {
            return;
        }

        try {
            const newPartnerId = await this.orm.create("res.partner", [
                {
                    name: contactName.trim(),
                    parent_id: cashCustomerId,
                    type: "contact",
                    customer_rank: 1,
                },
            ]);

            await this.pos.loadNewPartner(newPartnerId);
            const newPartner = this.pos.models["res.partner"].find(
                (p) => p.id === newPartnerId
            );
            if (newPartner && this.props.getPayload) {
                this.props.getPayload(newPartner);
            }
            this.notification.add(
                _t("Customer '%s' created under %s", contactName, cashCustomerName),
                { type: "success" }
            );
        } catch (err) {
            this.notification.add(_t("Failed to create customer: %s", err.message), {
                type: "danger",
            });
        }
    },
});
