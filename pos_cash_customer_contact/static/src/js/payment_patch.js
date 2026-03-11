/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { CustomerPopup } from "./customer_popup";

patch(ProductScreen.prototype, {

    async _onClickPay() {

        const order = this.pos.get_order();

        if (!order.get_partner()) {

            await this.popup.add(CustomerPopup);

        }

        return super._onClickPay(...arguments);

    }

});