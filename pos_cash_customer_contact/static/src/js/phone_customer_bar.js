/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

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

    async onCreateCustomer() {
        if (!this.state.phone || this.state.creating) return;
        this.state.creating = true;

        try {
            // Step 1: Create the partner in the backend
            const partnerId = await this.orm.create("res.partner", [{
                name: this.state.phone,
                phone: this.state.phone,
                customer_rank: 1,
            }]);

            // Step 2: Load the new partner record into the POS data cache
            // this.pos.data.read() is the correct Odoo 17 API
            await this.pos.data.read("res.partner", [partnerId]);

            // Step 3: Now it's in the model — find and assign it
            const newPartner = this.pos.models["res.partner"].find(
                (p) => p.id === partnerId
            );

            if (newPartner) {
                this.pos.getOrder().setPartner(newPartner);
                this.state.found = true;
                this.state.customerName = newPartner.name;
                this.notification.add(
                    `Customer created: ${newPartner.name}`,
                    { type: "success", sticky: false }
                );
            } else {
                throw new Error("Partner not found after load");
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