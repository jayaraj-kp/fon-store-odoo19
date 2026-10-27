/** @odoo-module */
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

const { DateTime } = luxon;

/**
 * 1) Some Odoo 19 builds pick a pricelist rule in the POS WITHOUT checking the
 *    rule's start/end date ("findBestRule" ignores date_start / date_end).
 *    We add that check, so a rule is used only while its window is active.
 *    The class is patched through a live pricelist record, so no import path
 *    of the model file is needed.
 *
 * 2) The price of the lines of an open order is recalculated when the order is
 *    selected, when going to payment, and every minute, so a price that
 *    starts/ends while the order is open is applied/reverted automatically.
 *    Only lines whose product has a pricelist rule are touched; manually
 *    edited prices and paid orders are left alone.
 *
 * 3) NEW: the POS loads pricelist rules only once when it opens. Rules that are
 *    created or changed afterwards (new scheduled price, changed start/end)
 *    are now fetched from the server every minute, when an order is selected
 *    and before payment, and merged into the POS local data.
 */

const patchedPrototypes = new WeakSet();

const RULE_FIELDS = [
    "pricelist_id",
    "product_tmpl_id",
    "product_id",
    "categ_id",
    "applied_on",
    "compute_price",
    "fixed_price",
    "percent_price",
    "price_discount",
    "price_surcharge",
    "base",
    "base_pricelist_id",
    "min_quantity",
    "date_start",
    "date_end",
    "write_date",
];
const RULE_MANY2ONE = [
    "pricelist_id",
    "product_tmpl_id",
    "product_id",
    "categ_id",
    "base_pricelist_id",
];

function toMillis(value) {
    if (!value) {
        return null;
    }
    if (typeof value === "string") {
        let dt = DateTime.fromISO(value);
        if (!dt.isValid) {
            dt = DateTime.fromSQL(value, { zone: "utc" });
        }
        return dt.isValid ? dt.toMillis() : null;
    }
    const ms = value.valueOf();
    return Number.isFinite(ms) ? ms : null;
}

function installPricelistDateCheck(pricelist) {
    if (!pricelist) {
        return;
    }
    const proto = Object.getPrototypeOf(pricelist);
    if (!proto || patchedPrototypes.has(proto) || typeof proto.findBestRule !== "function") {
        return;
    }
    patchedPrototypes.add(proto);
    patch(proto, {
        findBestRule(rules, quantity) {
            const now = Date.now();
            const validRules = (rules || []).filter((rule) => {
                const start = toMillis(rule.date_start);
                const end = toMillis(rule.date_end);
                return !(start !== null && start > now) && !(end !== null && end < now);
            });
            return super.findBestRule(validRules, quantity);
        },
    });
    console.info("[product_scheduled_price] pricelist date check installed");
}

patch(PosStore.prototype, {
    async setup() {
        const res = await super.setup(...arguments);
        try {
            installPricelistDateCheck(this.models["product.pricelist"].getFirst());
        } catch (error) {
            console.warn("[product_scheduled_price] could not install date check", error);
        }
        this._scheduledPriceTimer = setInterval(
            () => this.syncAndRefreshScheduledPrices(),
            60000
        );
        this.syncAndRefreshScheduledPrices();
        return res;
    },

    setOrder(order) {
        const res = super.setOrder(...arguments);
        this.refreshScheduledPrices(order);
        // also pull the latest rules from the server, then recalculate
        this.syncAndRefreshScheduledPrices(order);
        return res;
    },

    async pay() {
        await this.syncScheduledRules();
        this.refreshScheduledPrices();
        return await super.pay(...arguments);
    },

    async syncAndRefreshScheduledPrices(order = null) {
        await this.syncScheduledRules();
        this.refreshScheduledPrices(order);
    },

    /**
     * Fetch new/changed pricelist rules from the server and merge them into
     * the POS local data. First run: all rules that have an end date
     * (scheduled rules, including expired ones). Next runs: only rules
     * written since the previous sync.
     */
    async syncScheduledRules() {
        if (this._scheduledSyncBusy) {
            return;
        }
        this._scheduledSyncBusy = true;
        try {
            const orm = (this.data && this.data.orm) || this.orm;
            if (!orm) {
                return;
            }
            const domain = this._scheduledLastSync
                ? [["write_date", ">", this._scheduledLastSync]]
                : [["date_end", "!=", false]];
            // 5 minutes safety margin for clock differences; reloading the
            // same rule twice is harmless
            const syncedAt = DateTime.utc()
                .minus({ minutes: 5 })
                .toFormat("yyyy-MM-dd HH:mm:ss");
            const rows = await orm.searchRead("product.pricelist.item", domain, RULE_FIELDS);
            this._scheduledLastSync = syncedAt;
            if (!rows.length) {
                return;
            }
            const knownPricelists = new Set(this.models["product.pricelist"].map((p) => p.id));
            const data = [];
            for (const row of rows) {
                const rule = { ...row };
                for (const name of RULE_MANY2ONE) {
                    if (Array.isArray(rule[name])) {
                        rule[name] = rule[name][0];
                    }
                }
                delete rule.write_date;
                if (!knownPricelists.has(rule.pricelist_id)) {
                    continue;
                }
                if (
                    rule.product_tmpl_id &&
                    !this.models["product.template"].get(rule.product_tmpl_id)
                ) {
                    continue;
                }
                data.push(rule);
            }
            if (data.length) {
                this.models.loadData({ "product.pricelist.item": data });
                console.info(
                    "[product_scheduled_price] synced pricelist rules:",
                    data.map((r) => r.id)
                );
            }
        } catch (error) {
            console.warn("[product_scheduled_price] rule sync failed", error);
        } finally {
            this._scheduledSyncBusy = false;
        }
    },

    refreshScheduledPrices(order = null) {
        try {
            order = order || this.getOrder();
            if (!order || order.finalized || !order.pricelist_id) {
                return;
            }
            const pricelist = order.pricelist_id;
            installPricelistDateCheck(pricelist);
            for (const line of order.getLinesToCompute()) {
                const tmpl = line.product_id && line.product_id.product_tmpl_id;
                if (!tmpl || !pricelist.getRulesByTmplId(tmpl.id).length) {
                    continue;
                }
                const newPrice = tmpl.getPrice(
                    pricelist,
                    line.getQuantity(),
                    line.getPriceExtra(),
                    false,
                    line.product_id
                );
                if (Math.abs(newPrice - line.price_unit) > 0.0001) {
                    line.setUnitPrice(newPrice);
                }
            }
        } catch (error) {
            console.warn("[product_scheduled_price] price refresh failed", error);
        }
    },
});

///** @odoo-module */
//import { PosStore } from "@point_of_sale/app/services/pos_store";
//import { patch } from "@web/core/utils/patch";
//
//const { DateTime } = luxon;
//
///**
// * 1) Some Odoo 19 builds pick a pricelist rule in the POS WITHOUT checking the
// *    rule's start/end date ("findBestRule" ignores date_start / date_end).
// *    We add that check, so a rule is used only while its window is active.
// *    The class is patched through a live pricelist record, so no import path
// *    of the model file is needed.
// *
// * 2) The price of the lines of an open order is recalculated when the order is
// *    selected, when going to payment, and every minute, so a price that
// *    starts/ends while the order is open is applied/reverted automatically.
// *    Only lines whose product has a pricelist rule are touched; manually
// *    edited prices and paid orders are left alone.
// */
//
//const patchedPrototypes = new WeakSet();
//
//function toMillis(value) {
//    if (!value) {
//        return null;
//    }
//    if (typeof value === "string") {
//        let dt = DateTime.fromISO(value);
//        if (!dt.isValid) {
//            dt = DateTime.fromSQL(value, { zone: "utc" });
//        }
//        return dt.isValid ? dt.toMillis() : null;
//    }
//    const ms = value.valueOf();
//    return Number.isFinite(ms) ? ms : null;
//}
//
//function installPricelistDateCheck(pricelist) {
//    if (!pricelist) {
//        return;
//    }
//    const proto = Object.getPrototypeOf(pricelist);
//    if (!proto || patchedPrototypes.has(proto) || typeof proto.findBestRule !== "function") {
//        return;
//    }
//    patchedPrototypes.add(proto);
//    patch(proto, {
//        findBestRule(rules, quantity) {
//            const now = Date.now();
//            const validRules = (rules || []).filter((rule) => {
//                const start = toMillis(rule.date_start);
//                const end = toMillis(rule.date_end);
//                return !(start !== null && start > now) && !(end !== null && end < now);
//            });
//            return super.findBestRule(validRules, quantity);
//        },
//    });
//    console.info("[product_scheduled_price] pricelist date check installed");
//}
//
//patch(PosStore.prototype, {
//    async setup() {
//        const res = await super.setup(...arguments);
//        try {
//            installPricelistDateCheck(this.models["product.pricelist"].getFirst());
//        } catch (error) {
//            console.warn("[product_scheduled_price] could not install date check", error);
//        }
//        this._scheduledPriceTimer = setInterval(() => this.refreshScheduledPrices(), 60000);
//        return res;
//    },
//
//    setOrder(order) {
//        const res = super.setOrder(...arguments);
//        this.refreshScheduledPrices(order);
//        return res;
//    },
//
//    async pay() {
//        this.refreshScheduledPrices();
//        return await super.pay(...arguments);
//    },
//
//    refreshScheduledPrices(order = null) {
//        try {
//            order = order || this.getOrder();
//            if (!order || order.finalized || !order.pricelist_id) {
//                return;
//            }
//            const pricelist = order.pricelist_id;
//            installPricelistDateCheck(pricelist);
//            for (const line of order.getLinesToCompute()) {
//                const tmpl = line.product_id && line.product_id.product_tmpl_id;
//                if (!tmpl || !pricelist.getRulesByTmplId(tmpl.id).length) {
//                    continue;
//                }
//                const newPrice = tmpl.getPrice(
//                    pricelist,
//                    line.getQuantity(),
//                    line.getPriceExtra(),
//                    false,
//                    line.product_id
//                );
//                if (Math.abs(newPrice - line.price_unit) > 0.0001) {
//                    line.setUnitPrice(newPrice);
//                }
//            }
//        } catch (error) {
//            console.warn("[product_scheduled_price] price refresh failed", error);
//        }
//    },
//});
