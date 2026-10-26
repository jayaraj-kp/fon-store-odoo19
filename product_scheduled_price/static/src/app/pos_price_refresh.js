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
 */

const patchedPrototypes = new WeakSet();

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
        this._scheduledPriceTimer = setInterval(() => this.refreshScheduledPrices(), 60000);
        return res;
    },

    setOrder(order) {
        const res = super.setOrder(...arguments);
        this.refreshScheduledPrices(order);
        return res;
    },

    async pay() {
        this.refreshScheduledPrices();
        return await super.pay(...arguments);
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
