/** @odoo-module */
// Hide Customer (.set-partner) button in POS - Odoo 19

import { patch } from "@web/core/utils/patch";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";

patch(ActionpadWidget.prototype, {
    setup() {
        super.setup(...arguments);
    },
    get showSetCustomer() {
        return false;
    },
});