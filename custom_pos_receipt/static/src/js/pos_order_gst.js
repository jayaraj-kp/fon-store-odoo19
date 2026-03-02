/** @odoo-module **/
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {

    getGstBreakdown() {
        const grouped = {};
        for (const line of this.get_orderlines()) {
            const lineTaxes = line.get_applicable_taxes();
            const linePrice = line.get_price_without_tax();
            for (const tax of lineTaxes) {
                const rate = tax.amount || 0;
                const key = `rate_${rate}`;
                if (!grouped[key]) {
                    grouped[key] = {
                        rate: rate,
                        label: rate === 0 ? "GST Exempt" : `GST @ ${rate}%`,
                        taxable: 0,
                        cgst: 0,
                        sgst: 0,
                    };
                }
                grouped[key].taxable += linePrice;
                const taxAmount = linePrice * (rate / 100);
                grouped[key].cgst += taxAmount / 2;
                grouped[key].sgst += taxAmount / 2;
            }
        }
        return Object.values(grouped).sort((a, b) => a.rate - b.rate);
    },

    getTotalTaxableAmount() {
        return this.get_orderlines().reduce((sum, l) => sum + l.get_price_without_tax(), 0);
    },

    getTotalCgst() {
        return this.getGstBreakdown().reduce((sum, g) => sum + g.cgst, 0);
    },

    getTotalSgst() {
        return this.getGstBreakdown().reduce((sum, g) => sum + g.sgst, 0);
    },
});