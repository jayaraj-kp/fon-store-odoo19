/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CustomerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { useService } from "@web/core/utils/hooks";
import { onMounted, useState } from "@odoo/owl";

patch(CustomerList.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.extraInfo = useState({});
        this._loadExtraInfo();
    },

    async _loadExtraInfo() {
        try {
            const partners = this.pos.models["res.partner"].getAll();
            const ids = partners.map((p) => p.id).filter((id) => id > 0);
            if (!ids.length) return;

            const result = await this.orm.call(
                "res.partner",
                "get_pos_extra_info",
                [ids]
            );
            // result is a dict {id: {last_invoice_name, ...}}
            Object.assign(this.extraInfo, result);
        } catch (e) {
            console.warn("POS Extra Info: failed to load", e);
        }
    },

    getExtraInfo(partnerId) {
        return this.extraInfo[partnerId] || {
            last_invoice_name: "",
            last_invoice_date: "",
            invoice_count: 0,
            tags: "",
        };
    },
});
