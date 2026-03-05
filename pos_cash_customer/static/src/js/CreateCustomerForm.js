/** @odoo-module **/

/**
 * Odoo 19 CE — patch PartnerEditor to:
 *   1. Auto-set parent_id = CASH CUSTOMER when creating a new contact
 *   2. Show a "Parent Account" info banner inside the form (via inline xml)
 */

import { Component, xml, onMounted } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { PartnerEditor } from "@point_of_sale/app/screens/partner_list/partner_editor/partner_editor";
import { usePos } from "@point_of_sale/app/store/pos_hook";

// ── Standalone "parent account" info row ─────────────────────────────────────
export class CashParentRow extends Component {
    static template = xml`
        <div t-if="props.cashCustomerName" class="cash-parent-row">
            <span class="cash-parent-icon">🏷️</span>
            <span class="cash-parent-text">
                Parent Account: <strong t-esc="props.cashCustomerName"/>
            </span>
            <span class="cash-parent-badge">Auto-assigned</span>
        </div>
    `;
    static props = { cashCustomerName: { type: String, optional: true } };
}

// ── Patch PartnerEditor ───────────────────────────────────────────────────────
patch(PartnerEditor, {
    components: {
        ...PartnerEditor.components,
        CashParentRow,
    },
});

patch(PartnerEditor.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
        onMounted(() => this._prefillCashCustomerParent());
    },

    get cashCustomer() {
        return this.pos.getCashCustomer?.() || null;
    },

    _prefillCashCustomerParent() {
        const cashCustomer = this.cashCustomer;
        const isNew = !this.props.partner?.id;
        if (cashCustomer && isNew && this.changes && !this.changes.parent_id) {
            this.changes.parent_id = cashCustomer.id;
            this.changes.parent_name = cashCustomer.name;
            console.log(
                `[POS Cash Customer] ✅ parent_id pre-filled → ${cashCustomer.name} (id=${cashCustomer.id})`
            );
        }
    },

    async saveChanges() {
        const cashCustomer = this.cashCustomer;
        const isNew = !this.props.partner?.id;
        if (cashCustomer && isNew && this.changes && !this.changes.parent_id) {
            this.changes.parent_id = cashCustomer.id;
        }
        return await super.saveChanges(...arguments);
    },
});

