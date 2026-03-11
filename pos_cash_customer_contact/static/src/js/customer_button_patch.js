/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CustomerListScreen } from "@point_of_sale/app/screens/customer_list/customer_list_screen";
import { QuickCustomerPopup } from "./quick_customer_popup";

patch(CustomerListScreen.prototype, {

    async createPartner() {

        this.popup.add(QuickCustomerPopup);

    }

});