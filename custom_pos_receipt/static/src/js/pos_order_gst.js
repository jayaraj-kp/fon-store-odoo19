/** @odoo-module **/

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {

    /* ================= DATE FORMATTED dd/mm/yyyy ================= */
    getReceiptDateFormatted() {
        const d = this.date_order ? new Date(this.date_order) : new Date();
        const day   = String(d.getDate()).padStart(2, '0');
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const year  = d.getFullYear();
        return `${day}/${month}/${year}`;
    },

    /* ================= HELPER: format any date string to dd/mm/yyyy ================= */
    _formatDateDMY(dateStr) {
        if (!dateStr) return null;
        try {
            const d = new Date(dateStr);
            if (isNaN(d.getTime())) return null;
            const day   = String(d.getDate()).padStart(2, '0');
            const month = String(d.getMonth() + 1).padStart(2, '0');
            const year  = d.getFullYear();
            return `${day}/${month}/${year}`;
        } catch (e) {
            return null;
        }
    },

    /* ================= COMPANY NAME SPLIT INTO TWO LINES ================= */
    getCompanyNameLines() {
        const name = this.company?.name || '';
        const spaceIdx = name.indexOf(' ');
        if (spaceIdx > -1) {
            return [name.substring(0, spaceIdx), name.substring(spaceIdx + 1)];
        }
        return [name];
    },

    /* ================= GST BREAKDOWN ================= */
    getGstBreakdown() {
        const grouped = {};
        const lines = this.lines || this.orderlines || [];

        for (const line of lines) {
            const lineTaxes = line.tax_ids || [];
            const linePrice = line.price_subtotal || 0;

            for (const tax of lineTaxes) {
                const rate = tax.amount || 0;
                const key  = `rate_${rate}`;

                if (!grouped[key]) {
                    grouped[key] = {
                        rate:    rate,
                        label:   rate === 0 ? "GST Exempt" : `GST @ ${rate}%`,
                        taxable: 0,
                        cgst:    0,
                        sgst:    0,
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
        return lines.map((line, index) => {
            // Strip product codes like [FS1], [LC116] from start of name
            let name = line.product_id?.display_name || line.full_product_name || '';
            name = name.replace(/^\[.*?\]\s*/, '').trim();

            const lineTaxes = line.tax_ids || [];
            const gstRate   = lineTaxes.length > 0 ? (lineTaxes[0].amount || 0) : 0;

            return {
                sn:       index + 1,
                name:     name,
                qty:      line.qty || 0,
                uom:      line.product_id?.uom_id?.name || 'Units',
                rate:     line.price_unit || 0,
                gst:      gstRate,
                discount: line.discount || 0,
                total:    line.price_subtotal_incl || 0,
                note:     line.customerNote || '',
            };
        });
    },

    /* ================= TOTALS ================= */
    getGrandTotal() {
        return this.amount_total || 0;
    },

    getTotalSaved() {
        const lines = this.lines || this.orderlines || [];
        let totalSaved = 0;
        for (const line of lines) {
            const qty      = line.qty || 0;
            const price    = line.price_unit || 0;
            const discount = line.discount || 0;
            totalSaved += price * qty * (discount / 100);
        }
        return totalSaved;
    },

    /* ================= LOYALTY POINTS + EXPIRY ================= */
    /*
     * Returns an array of objects: { program, points, balance, expiry }
     * Works with Odoo 17/18/19 POS loyalty (couponPointChanges dict).
     */
    getLoyaltyInfo() {
        const result = [];
        try {
            // couponPointChanges: keyed by coupon id or 'new_N'
            const changes = this.couponPointChanges || {};

            for (const [, change] of Object.entries(changes)) {
                if (!change || typeof change !== 'object') continue;

                const pts = change.points || 0;
                if (pts === 0) continue;

                // Program name
                const program = change.program_id?.name
                    || change.program?.name
                    || 'Loyalty';

                // Coupon record carries balance & expiry
                const coupon  = change.coupon_id;
                let balance    = null;
                let expiry     = null;

                if (coupon && typeof coupon === 'object') {
                    const existing = typeof coupon.points === 'number' ? coupon.points : 0;
                    balance = Math.round((existing + pts) * 100) / 100;

                    const rawExpiry = coupon.expiration_date
                        || coupon.expiry_date
                        || coupon.validity_date
                        || null;
                    expiry = this._formatDateDMY(rawExpiry);
                }

                result.push({
                    program: program,
                    points:  pts % 1 === 0 ? pts : Math.round(pts * 100) / 100,
                    balance: balance,
                    expiry:  expiry,
                });
            }
        } catch (_e) {
            // Fail silently — loyalty block simply won't show
        }
        return result;
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
            if (n < 20)       return words[n];
            if (n < 100)      return tens[Math.floor(n / 10)] + (n % 10 ? " " + words[n % 10] : "");
            if (n < 1000)     return words[Math.floor(n / 100)] + " Hundred" + (n % 100 ? " " + convert(n % 100) : "");
            if (n < 100000)   return convert(Math.floor(n / 1000)) + " Thousand" + (n % 1000 ? " " + convert(n % 1000) : "");
            if (n < 10000000) return convert(Math.floor(n / 100000)) + " Lakh" + (n % 100000 ? " " + convert(n % 100000) : "");
            return convert(Math.floor(n / 10000000)) + " Crore" + (n % 10000000 ? " " + convert(n % 10000000) : "");
        }

        if (amount === 0) return "Zero Only";
        return convert(amount) + " Only";
    },

});