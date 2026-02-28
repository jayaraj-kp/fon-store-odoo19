/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";

/**
 * Safely extract parent_id as a number from any format Odoo might send:
 * false, null, undefined, number, string, [id, name], {id: ..., name: ...}
 */
function getParentId(partner) {
    const p = partner.parent_id;
    if (p === null || p === undefined || p === false) return null;
    if (typeof p === 'number') return p;
    if (typeof p === 'string') {
        const n = parseInt(p);
        return isNaN(n) ? null : n;
    }
    if (Array.isArray(p)) return typeof p[0] === 'number' ? p[0] : null;
    if (typeof p === 'object') return typeof p.id === 'number' ? p.id : null;
    return null;
}

function findCashCustomerId(model) {
    console.log("[POS_FILTER] ===== findCashCustomerId START - total partners:", model.length, "=====");

    // Log all partners so we can see what's in the model
    model.filter(() => true).forEach(p => {
        console.log(
            `[POS_FILTER] partner: id=${p.id} name="${p.name}" ` +
            `parent_id_raw=${JSON.stringify(p.parent_id)} parent_id_parsed=${getParentId(p)}`
        );
    });

    // Strategy 1: "Cash Customer" with no parent (ideal top-level record)
    let cc = model.find(p => p.name === "Cash Customer" && !getParentId(p));
    if (cc) {
        console.log("[POS_FILTER] Strategy 1 SUCCESS: id=", cc.id);
        return cc.id;
    }
    console.log("[POS_FILTER] Strategy 1 FAILED");

    // Strategy 2: Any "Cash Customer"
    cc = model.find(p => p.name === "Cash Customer");
    if (cc) {
        console.log("[POS_FILTER] Strategy 2 SUCCESS: id=", cc.id, "parent=", getParentId(cc));
        return cc.id;
    }
    console.log("[POS_FILTER] Strategy 2 FAILED");

    // Strategy 3: Case-insensitive
    cc = model.find(p => p.name?.toLowerCase() === "cash customer");
    if (cc) {
        console.log("[POS_FILTER] Strategy 3 SUCCESS: id=", cc.id);
        return cc.id;
    }
    console.log("[POS_FILTER] Strategy 3 FAILED - Cash Customer not in model at all!");
    return null;
}

patch(PartnerList.prototype, {
    setup() {
        super.setup();
        console.log("[POS_FILTER] ===== PartnerList setup() START =====");

        const model = this.pos.models["res.partner"];
        this._cashCustomerId = findCashCustomerId(model);

        console.log("[POS_FILTER] _cashCustomerId=", this._cashCustomerId);

        if (this._cashCustomerId !== null) {
            // Show only children of Cash Customer on initial load (no search)
            this.state.initialPartners = model.filter(
                p => getParentId(p) === this._cashCustomerId
            );
            console.log(
                "[POS_FILTER] initialPartners (children of Cash Customer):",
                this.state.initialPartners.map(p => `id=${p.id} name="${p.name}"`)
            );
        } else {
            // Fallback: show all partners that have a parent
            this.state.initialPartners = model.filter(p => !!getParentId(p));
            console.log(
                "[POS_FILTER] initialPartners FALLBACK (all contacts):",
                this.state.initialPartners.map(p => `id=${p.id} name="${p.name}"`)
            );
        }

        console.log("[POS_FILTER] ===== PartnerList setup() END =====");
    },

    getPartners(partners) {
        console.log("[POS_FILTER] ===== getPartners() START =====");
        console.log("[POS_FILTER] received", partners.length, "partners, _cashCustomerId=", this._cashCustomerId);

        partners.forEach(p => {
            console.log(
                `[POS_FILTER] incoming: id=${p.id} name="${p.name}" ` +
                `parent_id_raw=${JSON.stringify(p.parent_id)} parent_id_parsed=${getParentId(p)}`
            );
        });

        let filtered;

        if (this._cashCustomerId !== null) {
            filtered = partners.filter(p => {
                const pid = getParentId(p);
                const isCashCustomerItself = p.id === this._cashCustomerId;
                const isChild = pid === this._cashCustomerId;
                const keep = isChild && !isCashCustomerItself;
                console.log(
                    `[POS_FILTER] filter: id=${p.id} name="${p.name}" ` +
                    `pid=${pid} isChild=${isChild} isSelf=${isCashCustomerItself} keep=${keep}`
                );
                return keep;
            });
        } else {
            // No Cash Customer found in model — show all contacts that have a parent
            console.log("[POS_FILTER] No cashCustomerId — fallback: showing all partners with a parent");
            filtered = partners.filter(p => !!getParentId(p));
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