/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";

function getParentId(partner) {
    /** Extract numeric parent_id regardless of format */
    const p = partner.parent_id;
    if (p === null || p === undefined || p === false) return null;
    if (typeof p === 'number') return p;
    if (typeof p === 'string') return parseInt(p) || null;
    if (typeof p === 'object' && !Array.isArray(p)) return p.id ?? null;
    if (Array.isArray(p)) return p[0] ?? null;
    return null;
}

function findCashCustomerId(model) {
    console.log("[POS_FILTER] ===== findCashCustomerId START =====");
    console.log("[POS_FILTER] Total partners in model:", model.length);

    // Log ALL partners for full visibility
    model.filter(() => true).forEach(p => {
        const pid = getParentId(p);
        console.log(
            `[POS_FILTER] Partner id=${p.id} name="${p.name}" parent_id_raw=${JSON.stringify(p.parent_id)} parent_id_parsed=${pid}`
        );
    });

    // Strategy 1: Find "Cash Customer" with no parent (top-level)
    let cashCustomer = model.find(
        (p) => p.name === "Cash Customer" && !getParentId(p)
    );
    if (cashCustomer) {
        console.log("[POS_FILTER] Strategy 1 SUCCESS: Found top-level Cash Customer id=", cashCustomer.id);
        return cashCustomer.id;
    }
    console.log("[POS_FILTER] Strategy 1 FAILED: No top-level Cash Customer found");

    // Strategy 2: Find "Cash Customer" regardless of parent
    cashCustomer = model.find((p) => p.name === "Cash Customer");
    if (cashCustomer) {
        console.log("[POS_FILTER] Strategy 2 SUCCESS: Found Cash Customer id=", cashCustomer.id, "parent=", getParentId(cashCustomer));
        return cashCustomer.id;
    }
    console.log("[POS_FILTER] Strategy 2 FAILED: No Cash Customer found at all");

    // Strategy 3: Case-insensitive search
    cashCustomer = model.find((p) => p.name?.toLowerCase() === "cash customer");
    if (cashCustomer) {
        console.log("[POS_FILTER] Strategy 3 SUCCESS: Case-insensitive match id=", cashCustomer.id);
        return cashCustomer.id;
    }
    console.log("[POS_FILTER] Strategy 3 FAILED: No case-insensitive match");

    console.log("[POS_FILTER] ===== findCashCustomerId FAILED - returning null =====");
    return null;
}

patch(PartnerList.prototype, {
    setup() {
        super.setup();
        console.log("[POS_FILTER] ===== PartnerList setup() START =====");

        const model = this.pos.models["res.partner"];
        console.log("[POS_FILTER] model type:", typeof model, "length:", model?.length);

        this._cashCustomerId = findCashCustomerId(model);
        console.log("[POS_FILTER] _cashCustomerId set to:", this._cashCustomerId);

        // Set initialPartners
        if (this._cashCustomerId !== null) {
            this.state.initialPartners = model.filter(
                (p) => getParentId(p) === this._cashCustomerId
            );
            console.log(
                "[POS_FILTER] initialPartners (children of Cash Customer):",
                this.state.initialPartners.map(p => `id=${p.id} name="${p.name}"`)
            );
        } else {
            // Fallback: show all partners that have a parent (contacts)
            this.state.initialPartners = model.filter((p) => !!getParentId(p));
            console.log(
                "[POS_FILTER] initialPartners FALLBACK (all contacts with parent):",
                this.state.initialPartners.map(p => `id=${p.id} name="${p.name}"`)
            );
        }

        console.log("[POS_FILTER] ===== PartnerList setup() END =====");
    },

    getPartners(partners) {
        console.log("[POS_FILTER] ===== getPartners() START =====");
        console.log("[POS_FILTER] getPartners() received", partners.length, "partners");
        console.log("[POS_FILTER] _cashCustomerId:", this._cashCustomerId);

        // Log all incoming partners
        partners.forEach(p => {
            const pid = getParentId(p);
            console.log(
                `[POS_FILTER] incoming: id=${p.id} name="${p.name}" parent_id_raw=${JSON.stringify(p.parent_id)} parent_id_parsed=${pid}`
            );
        });

        let filtered;

        if (this._cashCustomerId !== null) {
            filtered = partners.filter((p) => {
                const pid = getParentId(p);
                const match = pid === this._cashCustomerId;
                console.log(
                    `[POS_FILTER] filter check: id=${p.id} name="${p.name}" pid=${pid} cashId=${this._cashCustomerId} match=${match}`
                );
                return match;
            });
        } else {
            // No Cash Customer found — show all partners that have a parent
            console.log("[POS_FILTER] No cashCustomerId — showing all contacts with a parent");
            filtered = partners.filter((p) => !!getParentId(p));
        }

        console.log(
            "[POS_FILTER] getPartners: in=", partners.length,
            "out=", filtered.length,
            filtered.map(p => `id=${p.id} name="${p.name}"`)
        );
        console.log("[POS_FILTER] ===== getPartners() END =====");

        return super.getPartners(filtered);
    },
});