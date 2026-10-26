/** @odoo-module */
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

/**
 * POS keeps the unit price of a line as it was when the product was added.
 * With scheduled prices the price can change later (the window starts or
 * ends) while the order is still open. This patch recalculates, from the
 * pricelist rules (which carry their own start/end time), the price of the
 * lines of the current unpaid order:
 *   - when the order is selected
 *   - when going to the payment screen
 *   - every minute for the order on screen
 * Only lines whose product has a pricelist rule are touched, and manually
 * edited prices are left alone.
 */
patch(PosStore.prototype, {
    async setup() {
        const res = await super.setup(...arguments);
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
