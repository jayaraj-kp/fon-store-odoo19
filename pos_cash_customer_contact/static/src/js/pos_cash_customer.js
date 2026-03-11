/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CustomerListScreen } from "@point_of_sale/app/screens/customer_list/customer_list_screen";

patch(CustomerListScreen.prototype, {

    async showCreateCustomer() {

        const cashCustomer = this.pos.models["res.partner"].find(
            (p) => p.name === "CASH CUSTOMER"
        );

        let parent_id = cashCustomer ? cashCustomer.id : false;

        const partner = {
            parent_id: parent_id,
        };

        const { confirmed, payload } = await this.editPartner(partner);

        if (confirmed) {

            payload.parent_id = parent_id;

            const newPartner = await this.pos.data.create("res.partner", [payload]);

            await this.pos.data.loadPartners();

            this.props.resolve(newPartner);
        }
    }

});