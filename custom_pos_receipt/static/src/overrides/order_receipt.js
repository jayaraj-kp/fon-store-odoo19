/** @odoo-module **/

import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { patch } from "@web/core/utils/patch";
import { amountToWords } from "@custom_pos_receipt/utils/amount_in_words";

patch(OrderReceipt.prototype, {

    /**
     * Debug helper - open browser console to see what fields are available
     * Remove this after confirming it works
     */
    get debugReceiptData() {
        console.log("=== POS RECEIPT DATA ===", JSON.stringify(this.props.data, null, 2));
        return '';
    },

    /**
     * Tries every known Odoo 16/17/18/19 field name for grand total
     */
    get totalAmountInWords() {
        try {
            const d = this.props.data;
            if (!d) return '';

            // Try all known field names across Odoo versions
            const total =
                d.amount_total           ??   // Odoo 16/17
                d.total_with_tax         ??   // Some versions
                d.totalWithTax           ??   // camelCase variant
                d.grandTotal             ??   // another variant
                d.total                  ??   // simple
                d.Total                  ??   // capitalized
                // Parse from formatted string as last resort
                this._parseFormattedTotal(d) ??
                0;

            const num = parseFloat(total);
            console.log("=== TOTAL FOR WORDS ===", num);
            if (!num || isNaN(num)) return 'Amount not available';
            return amountToWords(num);
        } catch(e) {
            console.error("amountInWords error:", e);
            return '';
        }
    },

    /**
     * Last resort: try to find total from payment lines or tax totals
     */
    _parseFormattedTotal(d) {
        try {
            // Try from payment lines sum
            if (d.paymentlines && d.paymentlines.length) {
                const sum = d.paymentlines.reduce((s, p) => s + parseFloat(p.amount || 0), 0);
                if (sum > 0) return sum;
            }
            // Try from tax_totals
            if (d.tax_totals && d.tax_totals.amount_total) {
                return d.tax_totals.amount_total;
            }
            // Try amount from orderlines sum
            if (d.orderlines && d.orderlines.length) {
                return d.orderlines.reduce((s, l) =>
                    s + parseFloat(l.price_with_tax || l.priceWithTax || l.price || 0), 0);
            }
        } catch(e) {}
        return null;
    },

    get gstBreakdown() {
        try {
            const d = this.props.data;
            if (!d) return [];

            // Support all line array names
            const lines =
                d.lines        ??
                d.orderlines   ??
                d.order_lines  ??
                [];

            if (!lines.length) {
                console.log("=== NO LINES FOUND in receipt data ===", Object.keys(d));
                return [];
            }

            const breakdown = {};

            for (const line of lines) {
                const taxes = line.taxes || line.tax_ids || [];
                const base  = parseFloat(
                    line.price_subtotal ??
                    line.priceSubtotal  ??
                    line.price_without_tax ??
                    0
                );

                if (!taxes.length) {
                    if (!breakdown['exempt'])
                        breakdown['exempt'] = { label: 'GST Exempt', rate: -1, taxable: 0, cgst: 0, sgst: 0 };
                    breakdown['exempt'].taxable += base;
                } else {
                    let totalPct = 0, cgstAmt = 0, sgstAmt = 0;
                    for (const tax of taxes) {
                        const name = (tax.name || '').toUpperCase();
                        const pct  = parseFloat(tax.amount || 0);
                        const amt  = tax.tax_amount != null
                                     ? parseFloat(tax.tax_amount)
                                     : base * (pct / 100);
                        if (name.includes('CGST')) {
                            cgstAmt += amt; totalPct += pct;
                        } else if (name.includes('SGST') || name.includes('UTGST')) {
                            sgstAmt += amt; totalPct += pct;
                        } else {
                            cgstAmt += amt / 2;
                            sgstAmt += amt / 2;
                            totalPct += pct;
                        }
                    }
                    const rate = Math.round(totalPct);
                    const key  = `gst_${rate}`;
                    if (!breakdown[key])
                        breakdown[key] = { label: `GST @ ${rate}%`, rate, taxable: 0, cgst: 0, sgst: 0 };
                    breakdown[key].taxable += base;
                    breakdown[key].cgst    += cgstAmt;
                    breakdown[key].sgst    += sgstAmt;
                }
            }
            return Object.values(breakdown).sort((a, b) =>
                a.rate === -1 ? -1 : b.rate === -1 ? 1 : a.rate - b.rate
            );
        } catch(e) {
            console.error("gstBreakdown error:", e);
            return [];
        }
    },

    get gstBreakdownTotals() {
        const rows = this.gstBreakdown;
        return {
            taxable: rows.reduce((s, r) => s + r.taxable, 0),
            cgst:    rows.reduce((s, r) => s + r.cgst,    0),
            sgst:    rows.reduce((s, r) => s + r.sgst,    0),
        };
    },

    get totalSavings() {
        try {
            const d = this.props.data;
            const val = parseFloat(
                d?.total_discount   ??
                d?.totalDiscount    ??
                d?.discount         ??
                d?.total_discount_amount ??
                0
            );
            console.log("=== SAVINGS ===", val, "keys:", Object.keys(d || {}));
            return val;
        } catch(e) { return 0; }
    },

    get hasSavings() {
        return this.totalSavings > 0;
    },
});
