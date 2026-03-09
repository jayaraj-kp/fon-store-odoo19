/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CustomerList } from "@point_of_sale/app/screens/customer_list/customer_list";
import { CreateContactPopup } from "./CreateContactPopup";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { onMounted } from "@odoo/owl";

/**
 * Patch CustomerList to:
 * 1. Auto-select CASH CUSTOMER as default when screen opens
 * 2. Override "Create" button to open simplified CreateContactPopup
 */
patch(CustomerList.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
        this.popup = useService("popup");

        onMounted(() => {
            this._setDefaultCashCustomer();
        });
    },

    /**
     * Pre-select the CASH CUSTOMER if no customer is set on the current order.
     */
    _setDefaultCashCustomer() {
        const order = this.pos.get_order();
        if (!order) return;

        // Only set default if no customer is already selected
        if (order.get_partner()) return;

        const cashCustomerId = this.pos.config.cash_customer_id;
        if (!cashCustomerId) return;

        const cashPartner = this.pos.models["res.partner"].find(
            (p) => p.id === cashCustomerId
        );
        if (cashPartner) {
            order.set_partner(cashPartner);
            // Update search state to show CASH CUSTOMER highlighted
            this.state.query = "";
        }
    },

    /**
     * Override create customer to open simplified popup instead of full form.
     */
    async createCustomer() {
        const result = await this.popup.add(CreateContactPopup, {
            title: "Create Contact",
        });

        if (result && result.confirmed && result.payload) {
            const newPartner = result.payload;
            // Set the newly created customer on the order
            const order = this.pos.get_order();
            if (order && newPartner) {
                order.set_partner(newPartner);
            }
            this.props.close();
        }
    },
});
