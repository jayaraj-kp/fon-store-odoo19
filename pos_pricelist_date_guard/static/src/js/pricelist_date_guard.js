/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

/*
 * POS Pricelist Date Guard
 *
 * Standard POS (Odoo 19) loads pricelist rules when the page opens and its
 * findBestRule() only compares the minimum quantity. A rule whose End Date
 * has passed (or whose Start Date is still in the future) therefore keeps
 * applying until the POS page is reloaded.
 *
 * This patch wraps findBestRule() so that rules outside their validity
 * window are ignored at the moment the price is calculated.
 */

const GUARD = "__posPricelistDateGuard";

function toMillis(value) {
    if (!value) {
        return null;
    }
    // luxon DateTime (what POS stores for datetime fields)
    if (typeof value.toMillis === "function") {
        return value.toMillis();
    }
    const ms = new Date(value).getTime();
    return Number.isNaN(ms) ? null : ms;
}

function isRuleActive(rule, now) {
    const start = toMillis(rule.date_start);
    const end = toMillis(rule.date_end);
    if (start !== null && start > now) {
        return false;
    }
    if (end !== null && end < now) {
        return false;
    }
    return true;
}

function installGuard(pos) {
    const pricelists = pos.models["product.pricelist"]?.getAll?.() || [];
    for (const pricelist of pricelists) {
        const proto = Object.getPrototypeOf(pricelist);
        if (!proto || proto[GUARD] || typeof proto.findBestRule !== "function") {
            continue;
        }
        const original = proto.findBestRule;
        proto.findBestRule = function (rules, quantity) {
            const now = Date.now();
            const validRules = (rules || []).filter((rule) => isRuleActive(rule, now));
            return original.call(this, validRules, quantity);
        };
        proto[GUARD] = true;
    }
}

patch(PosStore.prototype, {
    async afterProcessServerData() {
        const result = await super.afterProcessServerData(...arguments);
        installGuard(this);
        return result;
    },
});
