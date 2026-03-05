/** @odoo-module **/

/**
 * Odoo 19 CE — patch PartnerList screen to expose cashCustomer getter
 * so the XML template can show the banner.
 */

import { patch } from "@web/core/utils/patch";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { usePos } from "@point_of_sale/app/store/pos_hook";

patch(PartnerList.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
    },

    /** Exposes CASH CUSTOMER to the OWL template */
    get cashCustomer() {
        return this.pos.getCashCustomer?.() || null;
    },
});
