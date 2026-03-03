/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosOrder.prototype, 'custom_pos_receipt_patch', {

    getGstBreakdown() {
        const grouped = {};
        const lines = this.orderlines?.models || [];

        for (const line of lines) {
            const lineTaxes = line.tax_ids || [];
            const linePrice = line.price_subtotal || 0;

            for (const tax of lineTaxes) {
                const rate = tax.amount || 0;
                const key = `rate_${rate}`;

                if (!grouped[key]) {
                    grouped[key] = {
                        rate,
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

        return Object.values(grouped).sort((a,b) => a.rate - b.rate);
    },

    getTotalTaxableAmount() {
        return (this.orderlines?.models || []).reduce((sum, l) => sum + (l.price_subtotal || 0), 0);
    },

    getTotalCgst() {
        return this.getGstBreakdown().reduce((sum, g) => sum + g.cgst, 0);
    },

    getTotalSgst() {
        return this.getGstBreakdown().reduce((sum, g) => sum + g.sgst, 0);
    },

    getBeforeGrandTotal() {
        return this.getTotalTaxableAmount();
    },

    getGrandTotal() {
        return this.amount_total || 0;
    },

    getTotalSaved() {
        return (this.orderlines?.models || []).reduce((totalSaved, line) => {
            const lineTotal = (line.price_unit || 0) * (line.qty || 0);
            return totalSaved + (lineTotal * ((line.discount || 0)/100));
        }, 0);
    },

    getAmountInWords() {
        const amount = Math.floor(this.getGrandTotal());
        const words = [
            "Zero","One","Two","Three","Four","Five","Six","Seven","Eight","Nine","Ten",
            "Eleven","Twelve","Thirteen","Fourteen","Fifteen","Sixteen","Seventeen",
            "Eighteen","Nineteen"
        ];
        const tens = ["","","Twenty","Thirty","Forty","Fifty","Sixty","Seventy","Eighty","Ninety"];

        function convert(n) {
            if (n < 20) return words[n];
            if (n < 100) return tens[Math.floor(n/10)] + " " + words[n%10];
            if (n < 1000) return words[Math.floor(n/100)] + " Hundred " + convert(n%100);
            return n;
        }

        return convert(amount) + " Only";
    },

});