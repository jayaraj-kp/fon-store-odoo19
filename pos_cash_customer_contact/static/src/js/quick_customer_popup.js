/** @odoo-module **/

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";

export class QuickCustomerPopup extends Component {

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
    }

    async saveCustomer() {

        const name = this.refs.name.value;
        const phone = this.refs.phone.value;
        const email = this.refs.email.value;

        if (!name) {
            alert("Customer name required");
            return;
        }

        const cashCustomer = this.pos.models["res.partner"].find(
            (p) => p.name === "CASH CUSTOMER"
        );

        const partner = await this.orm.create(
            "res.partner",
            [{
                name: name,
                phone: phone,
                email: email,
                parent_id: cashCustomer ? cashCustomer.id : false,
            }]
        );

        await this.pos.loadPartners();

        const newPartner = this.pos.models["res.partner"].find(
            (p) => p.id === partner[0]
        );

        this.pos.get_order().set_partner(newPartner);

        this.props.close();
    }
}

QuickCustomerPopup.template = "pos_quick_cash_customer.QuickCustomerPopup";