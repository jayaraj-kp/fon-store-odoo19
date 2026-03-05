/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CreateEditPartner } from "@point_of_sale/app/screens/partner_list/partner_editor/partner_editor";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { onMounted } from "@odoo/owl";

patch(CreateEditPartner.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();

        onMounted(() => {
            this._prefillCashCustomerParent();
        });
    },

    /**
     * When the form is opened for creating a NEW customer,
     * pre-fill the parent_id with the CASH CUSTOMER partner.
     */
    _prefillCashCustomerParent() {
        const cashCustomer = this.pos.getCashCustomer
            ? this.pos.getCashCustomer()
            : null;

        // Only prefill if this is a NEW partner (no existing id)
        const isNew = !this.props.partner || !this.props.partner.id;

        if (cashCustomer && isNew) {
            // Set parent_id in the changes state so it gets saved
            if (this.changes) {
                if (!this.changes.parent_id) {
                    this.changes.parent_id = cashCustomer.id;
                    this.changes.parent_name = cashCustomer.name;
                    console.log(
                        `[POS Cash Customer] Pre-filled parent_id=${cashCustomer.id} (${cashCustomer.name})`
                    );
                }
            }
        }
    },

    /**
     * Override saveChanges to ensure parent_id is always set to CASH CUSTOMER
     * for new contacts if not explicitly changed.
     */
    async saveChanges() {
        const cashCustomer = this.pos.getCashCustomer
            ? this.pos.getCashCustomer()
            : null;
        const isNew = !this.props.partner || !this.props.partner.id;

        if (cashCustomer && isNew && this.changes && !this.changes.parent_id) {
            this.changes.parent_id = cashCustomer.id;
        }

        return await super.saveChanges(...arguments);
    },
});
