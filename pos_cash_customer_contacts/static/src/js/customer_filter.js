/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";

/**
 * POS Cash Customer Contacts Filter
 *
 * Root cause that was found:
 * - parent_id was UNDEFINED on all partners in the JS model
 * - This is because Odoo 19 POS does not load parent_id by default
 * - Fix: res_partner.py overrides _load_pos_data_fields() to add parent_id
 * - Now parent_id is available in JS and filtering works correctly
 *
 * Also: getPartners() was receiving 0 partners because super().getPartners()
 * applies its own internal search filter. We bypass super() for our case.
 */

function getParentId(partner) {
    const p = partner.parent_id;
    // After the Python fix, parent_id should be a number (the id)
    // but we handle all possible formats defensively
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

        console.log("[POS_FILTER] ===== setup() START - total partners in model:", model.length, "=====");

        // Log ALL partners with full detail so we can verify parent_id is loaded
        model.filter(() => true).forEach(p => {
            console.log(
                `[POS_FILTER] partner: id=${p.id} name="${p.name}"`,
                `| parent_id raw=`, p.parent_id,
                `| parent_id type=${typeof p.parent_id}`,
                `| parent_id parsed=`, getParentId(p)
            );
        });

        // Find Cash Customer (the parent record)
        const cashCustomer = model.find(p => p.name === "Cash Customer" && !getParentId(p));
        this._cashCustomerId = cashCustomer ? cashCustomer.id : null;

        console.log("[POS_FILTER] cashCustomer found:", cashCustomer?.id, cashCustomer?.name);
        console.log("[POS_FILTER] _cashCustomerId=", this._cashCustomerId);

        // Build the allowed IDs set (children of Cash Customer only)
        if (this._cashCustomerId !== null) {
            this._allowedPartnerIds = new Set(
                model
                    .filter(p => getParentId(p) === this._cashCustomerId)
                    .map(p => p.id)
            );
        } else {
            // Fallback: allow all partners that have any parent
            console.log("[POS_FILTER] FALLBACK: Cash Customer not found, allowing all contacts");
            this._allowedPartnerIds = new Set(
                model.filter(p => !!getParentId(p)).map(p => p.id)
            );
        }

        console.log("[POS_FILTER] _allowedPartnerIds:", [...this._allowedPartnerIds]);

        // Set initialPartners using the allowed IDs
        this.state.initialPartners = model.filter(p => this._allowedPartnerIds.has(p.id));

        console.log(
            "[POS_FILTER] initialPartners:", this.state.initialPartners.length,
            this.state.initialPartners.map(p => `id=${p.id} name="${p.name}"`)
        );
        console.log("[POS_FILTER] ===== setup() END =====");
    },

    getPartners(partners) {
        console.log("[POS_FILTER] getPartners() called with", partners.length, "partners");

        // Log what we receive
        partners.forEach(p => {
            console.log(
                `[POS_FILTER] getPartners input: id=${p.id} name="${p.name}"`,
                `parent_id raw=`, p.parent_id,
                `parent_id parsed=`, getParentId(p)
            );
        });

        // Update allowed IDs to include any newly loaded partners from get_new_partner
        if (this._cashCustomerId !== null) {
            // Add newly returned partners that are children of Cash Customer
            partners.forEach(p => {
                if (getParentId(p) === this._cashCustomerId) {
                    this._allowedPartnerIds.add(p.id);
                }
            });
        }

        // Filter to only allowed partners
        const filtered = partners.filter(p => {
            const allowed = this._allowedPartnerIds && this._allowedPartnerIds.has(p.id);
            console.log(`[POS_FILTER] filter: id=${p.id} name="${p.name}" allowed=${allowed}`);
            return allowed;
        });

        console.log(
            "[POS_FILTER] getPartners: in=", partners.length,
            "out=", filtered.length,
            filtered.map(p => `id=${p.id} name="${p.name}"`)
        );

        // IMPORTANT: Call super with our filtered list
        // super.getPartners() in Odoo 19 applies search term filtering
        // Since backend already filtered, pass filtered directly
        return super.getPartners(filtered);
    },
});