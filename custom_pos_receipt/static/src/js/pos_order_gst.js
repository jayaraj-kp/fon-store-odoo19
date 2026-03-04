/** @odoo-module **/

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {

    /* ================= GST BREAKDOWN ================= */
    getGstBreakdown() {
        const grouped = {};
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

    /* ================= LINE ITEMS FOR TABLE ================= */
    getReceiptLines() {
        const lines = this.lines || this.orderlines || [];
        return lines.map((line, index) => ({
            sn: index + 1,
            name: line.product_id?.display_name || line.full_product_name || '',
            qty: line.qty || 0,
            uom: line.product_id?.uom_id?.name || 'Units',
            rate: line.price_unit || 0,
            discount: line.discount || 0,
            total: line.price_subtotal_incl || 0,
            note: line.customerNote || '',
        }));
    },

    /* ================= CUSTOM TOTAL SECTION ================= */
    getBeforeGrandTotal() {
        return this.getTotalTaxableAmount();
    },

    getGrandTotal() {
        return this.amount_total || 0;
    },

    getTotalSaved() {
        const lines = this.lines || this.orderlines || [];
        let totalSaved = 0;
        for (const line of lines) {
            const qty = line.qty || 0;
            const unitPrice = line.price_unit || 0;
            const discount = line.discount || 0;
            const lineTotal = unitPrice * qty;
            const discountAmount = lineTotal * (discount / 100);
            totalSaved += discountAmount;
        }
        return totalSaved;
    },

    /* ================= AMOUNT IN WORDS ================= */
    getAmountInWords() {
        const amount = Math.floor(this.getGrandTotal());

        const words = [
            "Zero","One","Two","Three","Four","Five","Six","Seven","Eight","Nine","Ten",
            "Eleven","Twelve","Thirteen","Fourteen","Fifteen","Sixteen","Seventeen",
            "Eighteen","Nineteen"
        ];
        const tens = [
            "","","Twenty","Thirty","Forty","Fifty",
            "Sixty","Seventy","Eighty","Ninety"
        ];

        function convert(n) {
            if (n < 20) return words[n];
            if (n < 100) return tens[Math.floor(n / 10)] + (n % 10 ? " " + words[n % 10] : "");
            if (n < 1000) return words[Math.floor(n / 100)] + " Hundred" + (n % 100 ? " " + convert(n % 100) : "");
            if (n < 100000) return convert(Math.floor(n / 1000)) + " Thousand" + (n % 1000 ? " " + convert(n % 1000) : "");
            if (n < 10000000) return convert(Math.floor(n / 100000)) + " Lakh" + (n % 100000 ? " " + convert(n % 100000) : "");
            return convert(Math.floor(n / 10000000)) + " Crore" + (n % 10000000 ? " " + convert(n % 10000000) : "");
        }

        if (amount === 0) return "Zero Only";
        return convert(amount) + " Only";
    },

});