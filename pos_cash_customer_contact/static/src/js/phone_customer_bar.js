/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

export class PhoneCustomerBar extends Component {
    static template = "pos_cash_customer_contact.PhoneCustomerBar";
    static props = {};

    setup() {
        this.pos = usePos();
        this.state = useState({
            phone: "",
            customerName: "",
            found: false,
        });
    }

    onPhoneInput(ev) {
        const phone = ev.target.value.trim();
        this.state.phone = phone;

        if (!phone) {
            this.state.found = false;
            this.state.customerName = "";
            this.pos.getOrder().setPartner(null);
            return;
        }

        // Match on phone or mobile field
        const partner = this.pos.models["res.partner"].find(
            (p) => p.phone === phone || p.mobile === phone
        );

        if (partner) {
            this.pos.getOrder().setPartner(partner);
            this.state.found = true;
            this.state.customerName = partner.name;
        } else {
            this.state.found = false;
            this.state.customerName = "";
        }
    }

    onClear() {
        this.state.phone = "";
        this.state.found = false;
        this.state.customerName = "";
        this.pos.getOrder().setPartner(null);
    }
}

// Register PhoneCustomerBar into ProductScreen so the XML template can use it
patch(ProductScreen, {
    components: {
        ...ProductScreen.components,
        PhoneCustomerBar,
    },
});