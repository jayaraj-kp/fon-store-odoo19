/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

const CASH_CUSTOMER_NAME = "CASH CUSTOMER"; // Must match exactly in Contacts

export class PhoneCustomerBar extends Component {
    static template = "pos_cash_customer_contact.PhoneCustomerBar";
    static props = {};

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            phone: "",
            customerName: "",
            found: false,
            creating: false,
        });
    }

    onPhoneInput(ev) {
        const phone = ev.target.value.trim();
        this.state.phone = phone;
        this.state.found = false;
        this.state.customerName = "";

        if (!phone) {
            this.pos.getOrder().setPartner(false);
            return;
        }

        const partner = this.pos.models["res.partner"].find(
            (p) => p.phone === phone || p.mobile === phone
        );

        if (partner) {
            this.pos.getOrder().setPartner(partner);
            this.state.found = true;
            this.state.customerName = partner.name;
        } else {
            this.pos.getOrder().setPartner(false);
        }
    }

    onClear() {
        this.state.phone = "";
        this.state.found = false;
        this.state.customerName = "";
        this.state.creating = false;
        this.pos.getOrder().setPartner(false);
    }

    /**
     * Find the "CASH CUSTOMER" parent partner ID from backend.
     * If it doesn't exist yet, create it automatically.
     */
    async _getCashCustomerParentId() {
        const results = await this.orm.searchRead(
            "res.partner",
            [["name", "=", CASH_CUSTOMER_NAME], ["is_company", "=", true]],
            ["id"],
            { limit: 1 }
        );

        if (results.length) {
            return results[0].id;
        }

        // Auto-create the CASH CUSTOMER parent if it doesn't exist
        const newId = await this.orm.create("res.partner", [{
            name: CASH_CUSTOMER_NAME,
            is_company: true,
            customer_rank: 1,
        }]);
        return Array.isArray(newId) ? newId[0] : newId;
    }

    async onCreateCustomer() {
        if (!this.state.phone || this.state.creating) return;
        this.state.creating = true;

        try {
            // Step 1: Get or create the CASH CUSTOMER parent
            const parentId = await this._getCashCustomerParentId();

            // Step 2: Create the new contact as a child of CASH CUSTOMER
            const rawId = await this.orm.create("res.partner", [{
                name: this.state.phone,
                phone: this.state.phone,
                parent_id: parentId,
                customer_rank: 1,
            }]);
            const partnerId = Array.isArray(rawId) ? rawId[0] : rawId;

            // Step 3: Pull new partner into POS model cache
            await this.pos.data.searchRead(
                "res.partner",
                [["id", "=", partnerId]],
                [],
                { load: false }
            );

            // Step 4: Assign to current order
            const newPartner = this.pos.models["res.partner"].find(
                (p) => p.id === partnerId
            );

            if (newPartner) {
                this.pos.getOrder().setPartner(newPartner);
                this.state.found = true;
                this.state.customerName = newPartner.name;
                this.notification.add(
                    `Customer created under ${CASH_CUSTOMER_NAME}`,
                    { type: "success", sticky: false }
                );
            } else {
                throw new Error("Partner not found in cache after load");
            }

        } catch (err) {
            console.error("Failed to create customer:", err);
            this.notification.add(
                "Could not create customer: " + (err.message || err),
                { type: "danger", sticky: false }
            );
        } finally {
            this.state.creating = false;
        }
    }
}

patch(ProductScreen, {
    components: {
        ...ProductScreen.components,
        PhoneCustomerBar,
    },
});