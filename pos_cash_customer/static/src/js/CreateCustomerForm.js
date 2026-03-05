/** @odoo-module **/

/**
 * Odoo 19 CE — POS PartnerEditor patch.
 * Pre-fills parent_id = CASH CUSTOMER when creating a new contact from POS.
 */

import { patch } from "@web/core/utils/patch";
import { PartnerEditor } from "@point_of_sale/app/screens/partner_list/partner_editor/partner_editor";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { onMounted } from "@odoo/owl";

patch(PartnerEditor.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
        onMounted(() => this._prefillCashCustomerParent());
    },

    _prefillCashCustomerParent() {
        const cashCustomer = this.pos.getCashCustomer?.();
        const isNew = !this.props.partner?.id;
        if (cashCustomer && isNew && this.changes && !this.changes.parent_id) {
            this.changes.parent_id = cashCustomer.id;
            this.changes.parent_name = cashCustomer.name;
            console.log(
                `[POS Cash Customer] Pre-filled parent=${cashCustomer.name} (id=${cashCustomer.id})`
            );
        }
    },

    async saveChanges() {
        const cashCustomer = this.pos.getCashCustomer?.();
        const isNew = !this.props.partner?.id;
        if (cashCustomer && isNew && this.changes && !this.changes.parent_id) {
            this.changes.parent_id = cashCustomer.id;
        }
        return await super.saveChanges(...arguments);
    },
});
