//
//
//import { PosOrder } from "@point_of_sale/app/models/pos_order";
//import { patch } from "@web/core/utils/patch";
//
//patch(PosOrder.prototype, {
//
//    /* ================= DATE FORMATTED dd/mm/yyyy ================= */
//    getReceiptDateFormatted() {
//        const d = this.date_order ? new Date(this.date_order) : new Date();
//        const day   = String(d.getDate()).padStart(2, '0');
//        const month = String(d.getMonth() + 1).padStart(2, '0');
//        const year  = d.getFullYear();
//        return `${day}/${month}/${year}`;
//    },
//
//    /* ================= DATE + TIME: dd/mm/yyyy HH:MM ================= */
//    getReceiptDateTimeFormatted() {
//        const d = this.date_order ? new Date(this.date_order) : new Date();
//        const day   = String(d.getDate()).padStart(2, '0');
//        const month = String(d.getMonth() + 1).padStart(2, '0');
//        const year  = d.getFullYear();
//        const hours = String(d.getHours()).padStart(2, '0');
//        const mins  = String(d.getMinutes()).padStart(2, '0');
//        return `${day}/${month}/${year} ${hours}:${mins}`;
//    },
//
//    /* ================= HELPER: any date → dd/mm/yyyy ================= */
//    _formatDateDMY(dateStr) {
//        if (!dateStr) return null;
//        try {
//            const d = new Date(dateStr);
//            if (isNaN(d.getTime())) return null;
//            const day   = String(d.getDate()).padStart(2, '0');
//            const month = String(d.getMonth() + 1).padStart(2, '0');
//            return `${day}/${month}/${d.getFullYear()}`;
//        } catch (_) { return null; }
//    },
//
//    /* ================= CUSTOMER UNIQUE REF ================= */
//    getCustomerRef() {
//        const id = this.partner_id?.id || 0;
//        const padded = String(id).padStart(5, '0');
//
//        const cfg =
//            this.config ||
//            this.session?.config ||
//            this.pos?.config ||
//            null;
//
//        // Use the custom prefix field if set on pos.config (e.g. "KDTY" or "CHLR")
//        const customPrefix = (cfg?.pos_customer_prefix || '').toUpperCase().replace(/[^A-Z]/g, '');
//        if (customPrefix.length >= 2) {
//            return customPrefix + '-' + padded;
//        }
//
//        // Fallback: auto-derive from shop name — take up to 4 consonants
//        const shopName = (cfg?.name || '').toUpperCase().replace(/[^A-Z]/g, '');
//
//        let prefix = '';
//        if (shopName.length >= 2) {
//            const consonants = shopName.replace(/[AEIOU]/g, '');
//            if (consonants.length >= 2) {
//                prefix = consonants.substring(0, 4);
//            } else {
//                prefix = shopName.substring(0, 4);
//            }
//        } else {
//            prefix = (shopName + 'CST').substring(0, 3);
//        }
//
//        return prefix + '-' + padded;
//    },
//
//    /* ================= COMPANY NAME SPLIT ================= */
//    getCompanyNameLines() {
//        const name = this.company?.name || '';
//        const idx  = name.indexOf(' ');
//        if (idx > -1) return [name.substring(0, idx), name.substring(idx + 1)];
//        return [name];
//    },
//
//    /* ================= POS ADDRESS (highest priority) ================= */
//    /*
//     * Reads the "Receipt Address" fields entered directly on the POS
//     * Configuration form (Point of Sale → Configuration → Settings → your POS
//     * → "Receipt Address" tab).
//     *
//     * Returns an object with street, place, cityPin, and phone.
//     * Returns null if none of the POS-level address fields are filled.
//     *
//     * Priority chain in the receipt template:
//     *   1. getPosAddress()      ← fields on pos.config
//     *   2. getWarehouseInfo()   ← warehouse partner
//     *   3. company fallback
//     */
//    getPosAddress() {
//        const cfg =
//            this.config ||
//            this.session?.config ||
//            this.pos?.config ||
//            null;
//
//        if (!cfg) return null;
//        if (
//            !cfg.pos_address_street &&
//            !cfg.pos_address_place &&
//            !cfg.pos_address_city_pin &&
//            !cfg.pos_address_phone
//        ) return null;
//
//        return {
//            street:  cfg.pos_address_street  || '',
//            place:   cfg.pos_address_place   || '',
//            cityPin: cfg.pos_address_city_pin || '',
//            phone:   cfg.pos_address_phone   || '',
//        };
//    },
//
//    /* ================= WAREHOUSE / SHOP INFO ================= */
//    getWarehouseInfo() {
//        const wh =
//            this.config?.warehouse_id ||
//            this.session?.config?.warehouse_id ||
//            null;
//
//        if (!wh) return null;
//
//        const p = wh.partner_id || null;
//
//        return {
//            name:   wh.name   || '',
//            street: p?.street || '',
//            city:   p?.city   || '',
//            zip:    p?.zip    || '',
//            state:  p?.state_id?.name || '',
//            vat:    p?.vat    || '',
//            phone:  p?.phone  || p?.mobile || '',
//        };
//    },
//
//    /* ================= GST BREAKDOWN ================= */
//    getGstBreakdown() {
//        const grouped = {};
//        const lines   = this.lines || this.orderlines || [];
//
//        for (const line of lines) {
//            const lineTaxes = line.tax_ids || [];
//            const linePrice = line.price_subtotal || 0;
//
//            for (const tax of lineTaxes) {
//                const rate = tax.amount || 0;
//                const key  = `rate_${rate}`;
//                if (!grouped[key]) {
//                    grouped[key] = { rate, label: rate === 0 ? "GST Exempt" : `GST @ ${rate}%`, taxable: 0, cgst: 0, sgst: 0 };
//                }
//                grouped[key].taxable += linePrice;
//                const taxAmt = linePrice * (rate / 100);
//                grouped[key].cgst += taxAmt / 2;
//                grouped[key].sgst += taxAmt / 2;
//            }
//        }
//        return Object.values(grouped).sort((a, b) => a.rate - b.rate);
//    },
//
//    /*
//     * getTotalTaxableAmount — shows the original price BEFORE discount (and before rounding).
//     * This is what appears as "Total Amount" on the receipt.
//     * Sum of (price_unit × qty) for all lines, inclusive of tax rate.
//     * e.g. ₹200 item with 20% discount → Total Amount = ₹200
//     */
//    getTotalTaxableAmount() {
//        return (this.lines || this.orderlines || []).reduce((s, line) => {
//            const qty  = line.qty || 0;
//            const rate = line.price_unit || 0;
//            // price_unit is always the unit price before discount
//            // multiply by (1 + tax_rate/100) to get tax-inclusive original total
//            const taxRate = (line.tax_ids || []).reduce((t, tx) => t + (tx.amount || 0), 0);
//            return s + Math.round(rate * qty * (1 + taxRate / 100) * 100) / 100;
//        }, 0);
//    },
//
//    getTotalCgst() {
//        return this.getGstBreakdown().reduce((s, g) => s + g.cgst, 0);
//    },
//
//    getTotalSgst() {
//        return this.getGstBreakdown().reduce((s, g) => s + g.sgst, 0);
//    },
//
//    /* ================= LINE ITEMS FOR TABLE ================= */
//    getReceiptLines() {
//        return (this.lines || this.orderlines || []).map((line, index) => {
//            let name = (line.product_id?.display_name || line.full_product_name || '').replace(/^\[.*?\]\s*/, '').trim();
//            const gstRate = (line.tax_ids || []).length > 0 ? ((line.tax_ids[0].amount) || 0) : 0;
//            const qty      = line.qty || 0;
//            const rate     = line.price_unit || 0;
//            const discount = line.discount || 0;
//            const originalTotal = Math.round(rate * qty * 100) / 100;
//            return {
//                sn:            index + 1,
//                name,
//                qty,
//                uom:           line.product_id?.uom_id?.name || 'Units',
//                rate,
//                gst:           gstRate,
//                discount,
//                originalTotal,
//                total:         line.price_subtotal_incl || 0,
//                note:          line.customerNote || '',
//            };
//        });
//    },
//
//    /* ================= TOTALS ================= */
//
//    /*
//     * getRoundOff — difference between rounded and raw amount_total (after discount).
//     * Positive means rounding up, negative means rounding down.
//     * e.g. amount_total = 400.20 → rounded = 400 → roundOff = -0.20
//     * e.g. amount_total = 180.00 → rounded = 180 → roundOff = 0 (hidden)
//     */
//    getRoundOff() {
//        const raw     = this.amount_total || 0;
//        const rounded = Math.round(raw);
//        const diff    = Math.round((rounded - raw) * 100) / 100;
//        return diff === 0 ? 0 : diff;
//    },
//
//    /*
//     * getRoundedGrandTotal — amount_total (after discount) rounded to nearest integer.
//     */
//    getRoundedGrandTotal() {
//        return Math.round(this.amount_total || 0);
//    },
//
//    /*
//     * getGrandTotal — returns the ROUNDED final payable amount after discount.
//     * This is what appears as "Grand Total" on the receipt.
//     * e.g. ₹200 with 20% discount → amount_total = 180 → Grand Total = ₹180
//     * e.g. ₹400.20 no discount    → amount_total = 400.20 → Grand Total = ₹400
//     */
//    getGrandTotal() {
//        return this.getRoundedGrandTotal();
//    },
//
//    getTotalSaved() {
//        return (this.lines || this.orderlines || []).reduce((s, line) => {
//            return s + (line.price_unit || 0) * (line.qty || 0) * ((line.discount || 0) / 100);
//        }, 0);
//    },
//
//    /* ================= LOYALTY POINTS + EXPIRY ================= */
//    getLoyaltyInfo() {
//        const result = [];
//        try {
//            const changes = this.couponPointChanges || {};
//            for (const [, change] of Object.entries(changes)) {
//                if (!change || typeof change !== 'object') continue;
//                const pts = change.points || 0;
//                if (pts === 0) continue;
//
//                const program = change.program_id?.name || change.program?.name || 'Loyalty';
//                const coupon  = change.coupon_id;
//                let balance   = null;
//                let expiry    = null;
//
//                if (coupon && typeof coupon === 'object') {
//                    const existing = typeof coupon.points === 'number' ? coupon.points : 0;
//                    balance = Math.round((existing + pts) * 100) / 100;
//                    expiry  = this._formatDateDMY(
//                        coupon.expiration_date || coupon.expiry_date || coupon.validity_date || null
//                    );
//                }
//
//                result.push({
//                    program,
//                    points:  pts % 1 === 0 ? pts : Math.round(pts * 100) / 100,
//                    balance,
//                    expiry,
//                });
//            }
//        } catch (_) { /* fail silently */ }
//        return result;
//    },
//
//    /* ================= AMOUNT IN WORDS ================= */
//    /*
//     * Uses the rounded grand total so words match the Grand Total line.
//     * e.g. 400.20 → rounds to 400 → "Four Hundred Only"
//     */
//    getAmountInWords() {
//        const amount = this.getRoundedGrandTotal();
//        const w = ["Zero","One","Two","Three","Four","Five","Six","Seven","Eight","Nine","Ten",
//                   "Eleven","Twelve","Thirteen","Fourteen","Fifteen","Sixteen","Seventeen","Eighteen","Nineteen"];
//        const t = ["","","Twenty","Thirty","Forty","Fifty","Sixty","Seventy","Eighty","Ninety"];
//
//        function convert(n) {
//            if (n < 20)       return w[n];
//            if (n < 100)      return t[Math.floor(n/10)] + (n%10 ? " "+w[n%10] : "");
//            if (n < 1000)     return w[Math.floor(n/100)] + " Hundred" + (n%100 ? " "+convert(n%100) : "");
//            if (n < 100000)   return convert(Math.floor(n/1000)) + " Thousand" + (n%1000 ? " "+convert(n%1000) : "");
//            if (n < 10000000) return convert(Math.floor(n/100000)) + " Lakh" + (n%100000 ? " "+convert(n%100000) : "");
//            return convert(Math.floor(n/10000000)) + " Crore" + (n%10000000 ? " "+convert(n%10000000) : "");
//        }
//
//        return amount === 0 ? "Zero Only" : convert(amount) + " Only";
//    },
//
//    /* ================= CASHIER NAME ================= */
//    getCashierName() {
//        return (
//            this.employee_id?.name ||
//            this.cashier?.name ||
//            this.pos?.cashier?.name ||
//            ''
//        );
//    },
//
//    /* ================= CHARITY DONATION ================= */
//    getCharityDonation() {
//        return this._charity_donation_amount || 0;
//    },
//
//});
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

    /* ================= DATE + TIME: dd/mm/yyyy HH:MM ================= */
    getReceiptDateTimeFormatted() {
        const d = this.date_order ? new Date(this.date_order) : new Date();
        const day   = String(d.getDate()).padStart(2, '0');
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const year  = d.getFullYear();
        const hours = String(d.getHours()).padStart(2, '0');
        const mins  = String(d.getMinutes()).padStart(2, '0');
        return `${day}/${month}/${year} ${hours}:${mins}`;
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
    getCustomerRef() {
        const id = this.partner_id?.id || 0;
        const padded = String(id).padStart(5, '0');

        const cfg =
            this.config ||
            this.session?.config ||
            this.pos?.config ||
            null;

        // Use the custom prefix field if set on pos.config (e.g. "KDTY" or "CHLR")
        const customPrefix = (cfg?.pos_customer_prefix || '').toUpperCase().replace(/[^A-Z]/g, '');
        if (customPrefix.length >= 2) {
            return customPrefix + '-' + padded;
        }

        // Fallback: auto-derive from shop name — take up to 4 consonants
        const shopName = (cfg?.name || '').toUpperCase().replace(/[^A-Z]/g, '');

        let prefix = '';
        if (shopName.length >= 2) {
            const consonants = shopName.replace(/[AEIOU]/g, '');
            if (consonants.length >= 2) {
                prefix = consonants.substring(0, 4);
            } else {
                prefix = shopName.substring(0, 4);
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

    /* ================= POS ADDRESS ================= */
    getPosAddress() {
        const cfg =
            this.config ||
            this.session?.config ||
            this.pos?.config ||
            null;

        if (!cfg) return null;
        if (
            !cfg.pos_address_street &&
            !cfg.pos_address_place &&
            !cfg.pos_address_city_pin &&
            !cfg.pos_address_phone
        ) return null;

        return {
            street:  cfg.pos_address_street  || '',
            place:   cfg.pos_address_place   || '',
            cityPin: cfg.pos_address_city_pin || '',
            phone:   cfg.pos_address_phone   || '',
        };
    },

    /* ================= WAREHOUSE / SHOP INFO ================= */
    getWarehouseInfo() {
        const wh =
            this.config?.warehouse_id ||
            this.session?.config?.warehouse_id ||
            null;

        if (!wh) return null;

        const p = wh.partner_id || null;

        return {
            name:   wh.name   || '',
            street: p?.street || '',
            city:   p?.city   || '',
            zip:    p?.zip    || '',
            state:  p?.state_id?.name || '',
            vat:    p?.vat    || '',
            phone:  p?.phone  || p?.mobile || '',
        };
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

    /* ================= CHARITY DONATION ================= */
    /**
     * Returns the charity donation amount for this order.
     * Used by the receipt template to show the donation line
     * AND by other methods to subtract it from displayed totals.
     */
    getCharityDonation() {
        return this._charity_donation_amount || 0;
    },

    /* ================= LINE ITEMS FOR TABLE ================= */
    /**
     * Build the receipt line items array.
     *
     * The charity donation was added to the last line's price_unit via
     * setUnitPrice() in charity_button.js. We must subtract it from
     * that line's rate and total so the receipt shows the REAL product
     * price, not the inflated price-with-charity.
     *
     * e.g. mouse ₹993, charity ₹7 →
     *   line.price_unit = 1000  (bumped)
     *   We restore: rate = 1000 - 7 = 993
     *               total = price_subtotal_incl - 7 = 993
     */
    getReceiptLines() {
        const allLines    = this.lines || this.orderlines || [];
        const charityAmt  = this.getCharityDonation();
        const lastIndex   = allLines.length - 1;

        return allLines.map((line, index) => {
            let name = (line.product_id?.display_name || line.full_product_name || '')
                .replace(/^\[.*?\]\s*/, '').trim();

            const gstRate       = (line.tax_ids || []).length > 0 ? ((line.tax_ids[0].amount) || 0) : 0;
            const qty           = line.qty || 0;
            const discount      = line.discount || 0;

            // For the last line (where charity was applied), restore the original price
            const isCharityLine = charityAmt > 0 && index === lastIndex;
            const rate          = isCharityLine
                ? Math.round(((line.price_unit || 0) - charityAmt) * 100) / 100
                : (line.price_unit || 0);

            const originalTotal = Math.round(rate * qty * 100) / 100;

            // price_subtotal_incl has the bumped price — subtract charity for the last line
            const total = isCharityLine
                ? Math.round(((line.price_subtotal_incl || 0) - charityAmt) * 100) / 100
                : (line.price_subtotal_incl || 0);

            return {
                sn:            index + 1,
                name,
                qty,
                uom:           line.product_id?.uom_id?.name || 'Units',
                rate,
                gst:           gstRate,
                discount,
                originalTotal,
                total,
                note:          line.customerNote || '',
            };
        });
    },

    /* ================= TOTALS ================= */

    /**
     * getTotalTaxableAmount — sum of all line totals BEFORE discount,
     * with the charity amount EXCLUDED from the last line.
     *
     * e.g. mouse ₹1000 (bumped) with ₹7 charity →
     *   original price_unit = 993, taxRate = 0%
     *   getTotalTaxableAmount = 993
     */
    getTotalTaxableAmount() {
        const allLines   = this.lines || this.orderlines || [];
        const charityAmt = this.getCharityDonation();
        const lastIndex  = allLines.length - 1;

        return allLines.reduce((s, line, index) => {
            const qty     = line.qty || 0;
            const taxRate = (line.tax_ids || []).reduce((t, tx) => t + (tx.amount || 0), 0);

            // Restore original price_unit for the last (charity-bumped) line
            const rate = (charityAmt > 0 && index === lastIndex)
                ? Math.max(0, (line.price_unit || 0) - charityAmt)
                : (line.price_unit || 0);

            return s + Math.round(rate * qty * (1 + taxRate / 100) * 100) / 100;
        }, 0);
    },

    getTotalCgst() {
        return this.getGstBreakdown().reduce((s, g) => s + g.cgst, 0);
    },

    getTotalSgst() {
        return this.getGstBreakdown().reduce((s, g) => s + g.sgst, 0);
    },

    /**
     * getRoundOff — difference between rounded and raw amount_total
     * AFTER subtracting the charity donation.
     */
    getRoundOff() {
        const raw     = (this.amount_total || 0) - this.getCharityDonation();
        const rounded = Math.round(raw);
        const diff    = Math.round((rounded - raw) * 100) / 100;
        return diff === 0 ? 0 : diff;
    },

    /**
     * getRoundedGrandTotal — the product total (charity excluded), rounded.
     * e.g. amount_total=1000 with charity=7 → 1000-7=993 → 993
     */
    getRoundedGrandTotal() {
        return Math.round((this.amount_total || 0) - this.getCharityDonation());
    },

    /**
     * getGrandTotal — the amount the customer pays for PRODUCTS only.
     * Charity is shown separately on its own line below.
     */
    getGrandTotal() {
        return this.getRoundedGrandTotal();
    },

    /**
     * getTotalSaved — savings from discounts, using restored (non-charity) price.
     */
    getTotalSaved() {
        const allLines   = this.lines || this.orderlines || [];
        const charityAmt = this.getCharityDonation();
        const lastIndex  = allLines.length - 1;

        return allLines.reduce((s, line, index) => {
            const rate = (charityAmt > 0 && index === lastIndex)
                ? Math.max(0, (line.price_unit || 0) - charityAmt)
                : (line.price_unit || 0);
            return s + rate * (line.qty || 0) * ((line.discount || 0) / 100);
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
    /**
     * Uses the product grand total (charity excluded) so words match
     * the Grand Total line on the receipt.
     * e.g. amount_total=1000, charity=7 → words for ₹993
     */
    getAmountInWords() {
        const amount = this.getRoundedGrandTotal();
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

    /* ================= CASHIER NAME ================= */
    getCashierName() {
        return (
            this.employee_id?.name ||
            this.cashier?.name ||
            this.pos?.cashier?.name ||
            ''
        );
    },

});