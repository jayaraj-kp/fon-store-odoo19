/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CustomerPopup } from "./customer_popup";

patch(CustomerPopup.prototype, {

    onPhoneInput() {

        const phone = this.refs.phone.value;

        if (!phone) {
            return;
        }

        const partner = this.pos.models["res.partner"].find(
            (p) => p.phone === phone
        );

        if (partner) {

            this.refs.name.value = partner.name;

        }

    }

});