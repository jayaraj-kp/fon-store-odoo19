/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CustomerListScreen } from "@point_of_sale/app/screens/customer_list/customer_list_screen";

patch(CustomerListScreen.prototype, {

    async createPartner() {

        const cashCustomer = this.pos.db.get_partner_by_name("CASH CUSTOMER");

        let parent_id = false;

        if (cashCustomer) {
            parent_id = cashCustomer.id;
        }

        const { confirmed, payload } = await this.popup.add(
            this.pos.components.EditPartnerPopup,
            {
                partner: {
                    parent_id: parent_id,
                },
            }
        );

        if (confirmed) {

            payload.parent_id = parent_id;

            const partner = await this.pos.data.create("res.partner", [payload]);

            await this.pos.data.loadPartners();

            this.props.resolve(partner);
        }
    }

});