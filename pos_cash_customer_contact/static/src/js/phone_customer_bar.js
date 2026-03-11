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
            // Use false (not null) to safely unset partner in Odoo 17
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
            // Unset any previously assigned partner
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
            // Create partner in the backend
            const [partnerId] = await this.orm.create("res.partner", [{
                name: this.state.phone,   // default name = phone, cashier can rename later
                phone: this.state.phone,
                customer_rank: 1,
            }]);

            // Reload partners into the POS model cache
            await this.pos.models["res.partner"].load([partnerId]);

            // Find the freshly created partner and assign to order
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
            }
        } catch (err) {
            console.error("Failed to create customer:", err);
            this.notification.add(
                "Could not create customer. Check your connection.",
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