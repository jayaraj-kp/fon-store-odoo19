/** @odoo-module **/

/**
 * Odoo 19 CE — patch PartnerList to inject a CASH CUSTOMER banner
 * using a pure JS/OWL Component approach (no fragile XML xpath inheritance).
 */

import { Component, xml, useState, onWillStart } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { usePos } from "@point_of_sale/app/store/pos_hook";

// ── Standalone banner component ──────────────────────────────────────────────
export class CashCustomerBanner extends Component {
    static template = xml`
        <div t-if="cashCustomerName" class="cash-customer-banner">
            <span class="cash-customer-icon">👤</span>
            <span class="cash-customer-label">
                New contacts saved under: <strong t-esc="cashCustomerName"/>
            </span>
        </div>
    `;
    static props = { cashCustomerName: { type: String, optional: true } };

    get cashCustomerName() {
        return this.props.cashCustomerName || "";
    }
}

// ── Patch PartnerList to render the banner ────────────────────────────────────
patch(PartnerList, {
    components: {
        ...PartnerList.components,
        CashCustomerBanner,
    },
});

patch(PartnerList.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
    },

    get cashCustomer() {
        return this.pos.getCashCustomer?.() || null;
    },
});

