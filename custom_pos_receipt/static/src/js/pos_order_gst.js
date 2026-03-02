/** @odoo-module **/
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {

    getGstBreakdown() {
        const grouped = {};
        // Odoo 19 uses this.lines (not get_orderlines)
        const lines = this.lines || this.orderlines || [];

        for (const line of lines) {
            const lineTaxes = line.tax_ids || [];
            const linePrice = line.price_subtotal || 0;

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
        const lines = this.lines || this.orderlines || [];
        return lines.reduce((sum, l) => sum + (l.price_subtotal || 0), 0);
    },

    getTotalCgst() {
        return this.getGstBreakdown().reduce((sum, g) => sum + g.cgst, 0);
    },

    getTotalSgst() {
        return this.getGstBreakdown().reduce((sum, g) => sum + g.sgst, 0);
    },
});