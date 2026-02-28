/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";

/**
 * POS Cash Customer Contacts Filter
 *
 * STRATEGY:
 * - Backend (res_partner.py) already restricts ALL partner data to only
 *   Cash Customer's children + Cash Customer itself + current user.
 * - So the JS model["res.partner"] contains ONLY those records.
 * - We do NOT override getPartners() at all — let Odoo display whatever
 *   the backend sends. No JS filtering needed.
 * - We only override setup() to set initialPartners = children only
 *   (exclude Cash Customer parent record itself from the list).
 */

function getParentId(partner) {
    const p = partner.parent_id;
    if (p === null || p === undefined || p === false) return null;
    if (typeof p === 'number') return p;
    if (typeof p === 'string') { const n = parseInt(p); return isNaN(n) ? null : n; }
    if (Array.isArray(p)) return (typeof p[0] === 'number') ? p[0] : null;
    if (typeof p === 'object') return (typeof p.id === 'number') ? p.id : null;
    return null;
}

patch(PartnerList.prototype, {
    setup() {
        super.setup();

        const model = this.pos.models["res.partner"];

        console.log("[POS_FILTER] ===== setup() START =====");
        console.log("[POS_FILTER] Total partners in model:", model.length);

        // Log every partner so we can see exactly what's loaded
        model.filter(() => true).forEach(p => {
            console.log(
                `[POS_FILTER] model partner: id=${p.id} name="${p.name}"`,
                `parent_id_raw=`, p.parent_id,
                `parent_id_parsed=`, getParentId(p)
            );
        });

        // Find Cash Customer (the parent record itself)
        const cashCustomer = model.find(p => {
            const nameMatch = p.name === "Cash Customer";
            const noParent = !getParentId(p);
            console.log(`[POS_FILTER] checking for Cash Customer: id=${p.id} name="${p.name}" nameMatch=${nameMatch} noParent=${noParent}`);
            return nameMatch && noParent;
        });

        const cashCustomerId = cashCustomer ? cashCustomer.id : null;
        console.log("[POS_FILTER] cashCustomerId=", cashCustomerId);

        if (cashCustomerId) {
            // Show only children (exclude Cash Customer parent record itself)
            this.state.initialPartners = model.filter(p => getParentId(p) === cashCustomerId);
        } else {
            // Fallback: show everyone with a parent (all contacts)
            // This handles case where Cash Customer wasn't found
            this.state.initialPartners = model.filter(p => !!getParentId(p));
            console.log("[POS_FILTER] FALLBACK: cashCustomer not found in model, showing all contacts");
        }

        console.log(
            "[POS_FILTER] initialPartners count:", this.state.initialPartners.length,
            this.state.initialPartners.map(p => `id=${p.id} name="${p.name}"`)
        );
        console.log("[POS_FILTER] ===== setup() END =====");
    },

    // DO NOT override getPartners() — the backend already restricts data.
    // Overriding getPartners() was causing results from get_new_partner
    // (live search) to be filtered out. Let Odoo handle display naturally.
});