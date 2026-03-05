/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CustomerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState, xml } from "@odoo/owl";

/**
 * Simple inline dialog to collect a customer name.
 * Uses only @web and @odoo/owl — zero dependency on POS internal components.
 */
class CreateContactDialog extends Component {
    static template = xml`
        <Dialog title="props.title" size="'sm'">
            <div class="mb-3">
                <label class="form-label" for="new_customer_name">
                    Customer Name
                </label>
                <input
                    id="new_customer_name"
                    type="text"
                    class="form-control"
                    t-model="state.name"
                    placeholder="Enter customer name"
                    t-on-keydown="onKeydown"
                />
                <div t-if="state.error" class="text-danger mt-1" t-esc="state.error"/>
            </div>
            <t t-set-slot="footer">
                <button class="btn btn-primary" t-on-click="confirm">
                    Create Customer
                </button>
                <button class="btn btn-secondary" t-on-click="() => props.close()">
                    Cancel
                </button>
            </t>
        </Dialog>
    `;
    static components = { Dialog };
    static props = ["title", "close", "confirm"];

    setup() {
        this.state = useState({ name: "", error: "" });
    }

    onKeydown(ev) {
        if (ev.key === "Enter") {
            this.confirm();
        }
    }

    confirm() {
        const name = this.state.name.trim();
        if (!name) {
            this.state.error = _t("Please enter a customer name.");
            return;
        }
        this.props.confirm(name);
        this.props.close();
    }
}

/**
 * Patch CustomerList to redirect the "Create" button when a
 * cash_customer_id is configured: new partners are created as
 * child contacts under the master CASH CUSTOMER partner.
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

        // No cash customer configured → fall back to standard Odoo behaviour
        if (!cashCustomerId) {
            return super.createPartner(...arguments);
        }

        // Fetch the master partner name for display
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

        // Open a lightweight dialog to collect the new customer's name
        this.dialog.add(CreateContactDialog, {
            title: _t("New Customer (under %s)", cashCustomerName),
            confirm: async (customerName) => {
                try {
                    const newPartnerId = await this.orm.create("res.partner", [
                        {
                            name: customerName,
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
                        _t("'%s' created under %s", customerName, cashCustomerName),
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
    },
});