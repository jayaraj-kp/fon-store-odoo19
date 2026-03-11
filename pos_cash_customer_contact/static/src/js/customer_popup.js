/** @odoo-module **/

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";

export class CustomerPopup extends Component {

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
    }

    async saveCustomer() {

        const phone = this.refs.phone.value;
        const name = this.refs.name.value;

        if (!phone) {
            alert("Phone required");
            return;
        }

        const existing = this.pos.models["res.partner"].find(
            (p) => p.phone === phone
        );

        if (existing) {

            this.pos.get_order().set_partner(existing);
            this.props.close();
            return;

        }

        const cashCustomer = this.pos.models["res.partner"].find(
            (p) => p.name === "CASH CUSTOMER"
        );

        const partner_id = await this.orm.create("res.partner", [{
            name: name || phone,
            phone: phone,
            parent_id: cashCustomer ? cashCustomer.id : false
        }]);

        await this.pos.loadPartners();

        const partner = this.pos.models["res.partner"].find(
            (p) => p.id === partner_id[0]
        );

        this.pos.get_order().set_partner(partner);

        this.props.close();
    }

}

CustomerPopup.template = "pos_supermarket_customer.CustomerPopup";