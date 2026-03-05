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

    /* ================= HELPER: any date → dd/mm/yyyy ================= */
    _formatDateDMY(dateStr) {
        if (!dateStr) return null;
        try {
            const d = new Date(dateStr);
            if (isNaN(d.getTime())) return null;
            const day   = String(d.getDate()).padStart(2, '0');
            const month = String(d.getMonth() + 1).padStart(2, '0');
            return `${day}/${month}/${d.getFullYear()}`;
        } catch (_) { return null; }
    },

    /* ================= CUSTOMER UNIQUE REF ================= */
    /*
     * Builds a shop-prefixed customer ID.
     * Prefix = first 3 consonants of the POS config name (uppercased).
     * Falls back to first 3 letters if not enough consonants.
     * Examples:
     *   "Chelari POS"  → CHL-00014
     *   "Kondotty"     → KND-00014
     *   "FON Store"    → FNS-00014
     * If partner has an Internal Reference set, that is used as-is.
     */
    getCustomerRef() {
        const id = this.partner_id?.id || 0;
        const padded = String(id).padStart(5, '0');

        // Get POS config/shop name
        const shopName = (
            this.config?.name ||
            this.session?.config?.name ||
            this.pos?.config?.name ||
            ''
        ).toUpperCase().replace(/[^A-Z]/g, ''); // letters only

        let prefix = '';
        if (shopName.length >= 3) {
            // Extract first 3 consonants for a meaningful short code
            const consonants = shopName.replace(/[AEIOU]/g, '');
            if (consonants.length >= 3) {
                prefix = consonants.substring(0, 3);
            } else {
                // Not enough consonants — just take first 3 letters
                prefix = shopName.substring(0, 3);
            }
        } else {
            prefix = (shopName + 'CST').substring(0, 3);
        }

        return prefix + '-' + padded;
    },

    /* ================= COMPANY NAME SPLIT ================= */
    getCompanyNameLines() {
        const name = this.company?.name || '';
        const idx  = name.indexOf(' ');
        if (idx > -1) return [name.substring(0, idx), name.substring(idx + 1)];
        return [name];
    },

    /* ================= GST BREAKDOWN ================= */
    getGstBreakdown() {
        const grouped = {};
        const lines   = this.lines || this.orderlines || [];

        for (const line of lines) {
            const lineTaxes = line.tax_ids || [];
            const linePrice = line.price_subtotal || 0;

            for (const tax of lineTaxes) {
                const rate = tax.amount || 0;
                const key  = `rate_${rate}`;
                if (!grouped[key]) {
                    grouped[key] = { rate, label: rate === 0 ? "GST Exempt" : `GST @ ${rate}%`, taxable: 0, cgst: 0, sgst: 0 };
                }
                grouped[key].taxable += linePrice;
                const taxAmt = linePrice * (rate / 100);
                grouped[key].cgst += taxAmt / 2;
                grouped[key].sgst += taxAmt / 2;
            }
        }
        return Object.values(grouped).sort((a, b) => a.rate - b.rate);
    },

    getTotalTaxableAmount() {
        return (this.lines || this.orderlines || []).reduce((s, l) => s + (l.price_subtotal || 0), 0);
    },

    getTotalCgst() {
        return this.getGstBreakdown().reduce((s, g) => s + g.cgst, 0);
    },

    getTotalSgst() {
        return this.getGstBreakdown().reduce((s, g) => s + g.sgst, 0);
    },

    /* ================= LINE ITEMS FOR TABLE ================= */
    getReceiptLines() {
        return (this.lines || this.orderlines || []).map((line, index) => {
            // Strip product codes like [FS1], [LC116]
            let name = (line.product_id?.display_name || line.full_product_name || '').replace(/^\[.*?\]\s*/, '').trim();
            const gstRate = (line.tax_ids || []).length > 0 ? ((line.tax_ids[0].amount) || 0) : 0;
            const qty      = line.qty || 0;
            const rate     = line.price_unit || 0;
            const discount = line.discount || 0;
            // Original total before discount (rate × qty), rounded to 2dp
            const originalTotal = Math.round(rate * qty * 100) / 100;
            return {
                sn:            index + 1,
                name,
                qty,
                uom:           line.product_id?.uom_id?.name || 'Units',
                rate,
                gst:           gstRate,
                discount,
                originalTotal, // used for discount label "X% off on ₹ Y"
                total:         line.price_subtotal_incl || 0,
                note:          line.customerNote || '',
            };
        });
    },

    /* ================= TOTALS ================= */
    getGrandTotal() {
        return this.amount_total || 0;
    },

    /* Round to nearest whole rupee */
    getRoundedGrandTotal() {
        return Math.round(this.getGrandTotal());
    },

    /* Difference between rounded and actual (can be +/-) */
    getRoundOff() {
        const diff = Math.round((this.getRoundedGrandTotal() - this.getGrandTotal()) * 100) / 100;
        return diff === 0 ? 0 : diff;
    },

    getTotalSaved() {
        return (this.lines || this.orderlines || []).reduce((s, line) => {
            return s + (line.price_unit || 0) * (line.qty || 0) * ((line.discount || 0) / 100);
        }, 0);
    },

    /* ================= LOYALTY POINTS + EXPIRY ================= */
    getLoyaltyInfo() {
        const result = [];
        try {
            const changes = this.couponPointChanges || {};
            for (const [, change] of Object.entries(changes)) {
                if (!change || typeof change !== 'object') continue;
                const pts = change.points || 0;
                if (pts === 0) continue;

                const program = change.program_id?.name || change.program?.name || 'Loyalty';
                const coupon  = change.coupon_id;
                let balance   = null;
                let expiry    = null;

                if (coupon && typeof coupon === 'object') {
                    const existing = typeof coupon.points === 'number' ? coupon.points : 0;
                    balance = Math.round((existing + pts) * 100) / 100;
                    expiry  = this._formatDateDMY(
                        coupon.expiration_date || coupon.expiry_date || coupon.validity_date || null
                    );
                }

                result.push({
                    program,
                    points:  pts % 1 === 0 ? pts : Math.round(pts * 100) / 100,
                    balance,
                    expiry,
                });
            }
        } catch (_) { /* fail silently */ }
        return result;
    },

    /* ================= AMOUNT IN WORDS ================= */
    getAmountInWords() {
        const amount = Math.round(this.getGrandTotal());
        const w = ["Zero","One","Two","Three","Four","Five","Six","Seven","Eight","Nine","Ten",
                   "Eleven","Twelve","Thirteen","Fourteen","Fifteen","Sixteen","Seventeen","Eighteen","Nineteen"];
        const t = ["","","Twenty","Thirty","Forty","Fifty","Sixty","Seventy","Eighty","Ninety"];

        function convert(n) {
            if (n < 20)       return w[n];
            if (n < 100)      return t[Math.floor(n/10)] + (n%10 ? " "+w[n%10] : "");
            if (n < 1000)     return w[Math.floor(n/100)] + " Hundred" + (n%100 ? " "+convert(n%100) : "");
            if (n < 100000)   return convert(Math.floor(n/1000)) + " Thousand" + (n%1000 ? " "+convert(n%1000) : "");
            if (n < 10000000) return convert(Math.floor(n/100000)) + " Lakh" + (n%100000 ? " "+convert(n%100000) : "");
            return convert(Math.floor(n/10000000)) + " Crore" + (n%10000000 ? " "+convert(n%10000000) : "");
        }

        return amount === 0 ? "Zero Only" : convert(amount) + " Only";
    },

});