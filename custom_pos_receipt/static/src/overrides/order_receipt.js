/** @odoo-module **/

import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { patch } from "@web/core/utils/patch";
import { amountToWords } from "@custom_pos_receipt/utils/amount_in_words";

patch(OrderReceipt.prototype, {
    /**
     * Grand total amount in words
     */
    get totalAmountInWords() {
        const order = this.props.data;
        const total = order?.amount_total ?? order?.total_with_tax ?? 0;
        return amountToWords(total);
    },

    /**
     * Compute GST breakdown table grouped by tax rate
     * Returns array of: { rate_label, taxable, cgst, sgst }
     */
    get gstBreakdown() {
        const order = this.props.data;
        if (!order) return [];

        // Map to accumulate: key = gst_rate_percent => {taxable, cgst, sgst}
        const breakdown = {};

        const lines = order.lines || [];
        for (const line of lines) {
            const taxes = line.taxes || [];
            let lineTaxableBase = line.price_subtotal ?? 0;  // before tax

            if (taxes.length === 0) {
                // GST Exempt
                const key = 'exempt';
                if (!breakdown[key]) breakdown[key] = { label: 'GST Exempt', rate: -1, taxable: 0, cgst: 0, sgst: 0 };
                breakdown[key].taxable += lineTaxableBase;
            } else {
                // Sum all tax amounts for this line
                let totalTaxPct = 0;
                let cgstAmt = 0;
                let sgstAmt = 0;

                for (const tax of taxes) {
                    const name = (tax.name || '').toUpperCase();
                    const amount = tax.tax_amount ?? (lineTaxableBase * (tax.amount / 100));
                    if (name.includes('CGST')) {
                        cgstAmt += amount;
                        totalTaxPct += tax.amount || 0;
                    } else if (name.includes('SGST') || name.includes('UTGST')) {
                        sgstAmt += amount;
                        totalTaxPct += tax.amount || 0;
                    } else {
                        // Generic GST - split equally as CGST/SGST
                        cgstAmt += amount / 2;
                        sgstAmt += amount / 2;
                        totalTaxPct += tax.amount || 0;
                    }
                }

                // Round rate to nearest bracket
                const rate = Math.round(totalTaxPct);
                const key = `gst_${rate}`;
                if (!breakdown[key]) {
                    breakdown[key] = {
                        label: rate === 0 ? 'GST Exempt' : `GST @ ${rate}%`,
                        rate: rate,
                        taxable: 0,
                        cgst: 0,
                        sgst: 0
                    };
                }
                breakdown[key].taxable += lineTaxableBase;
                breakdown[key].cgst += cgstAmt;
                breakdown[key].sgst += sgstAmt;
            }
        }

        // Sort by rate ascending, exempt first
        return Object.values(breakdown).sort((a, b) => {
            if (a.rate === -1) return -1;
            if (b.rate === -1) return 1;
            return a.rate - b.rate;
        });
    },

    /**
     * Totals for the GST table footer
     */
    get gstBreakdownTotals() {
        const rows = this.gstBreakdown;
        return {
            taxable: rows.reduce((s, r) => s + r.taxable, 0),
            cgst: rows.reduce((s, r) => s + r.cgst, 0),
            sgst: rows.reduce((s, r) => s + r.sgst, 0),
        };
    },

    /**
     * Total discount / savings
     */
    get totalSavings() {
        const order = this.props.data;
        return order?.total_discount ?? order?.discount ?? 0;
    },
});