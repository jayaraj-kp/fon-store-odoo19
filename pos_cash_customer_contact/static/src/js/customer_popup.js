/** @odoo-module **/

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";

export class CustomerPopup extends Component {

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
        this.popup = useService("popup");
    }

}

CustomerPopup.template = "pos_cash_customer_contact.CustomerPopup";