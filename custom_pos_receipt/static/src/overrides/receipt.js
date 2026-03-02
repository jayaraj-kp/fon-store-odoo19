/** @odoo-module **/

import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { patch } from "@web/core/utils/patch";

patch(OrderReceipt.prototype, {
    /**
     * Build GST rows from order lines tax details.
     * Groups taxes by GST rate label, splits into CGST/SGST halves.
     */
    getGstRows() {
        const order = this.props.data;
        const taxGroups = {};

        // Iterate order lines to collect tax data
        if (order && order.orderlines) {
            for (const line of order.orderlines) {
                if (!line.taxes || line.taxes.length === 0) {
                    // GST Exempt
                    if (!taxGroups["GST Exempt"]) {
                        taxGroups["GST Exempt"] = { taxable: 0, gst: 0 };
                    }
                    taxGroups["GST Exempt"].taxable += line.price_subtotal || 0;
                } else {
                    for (const tax of line.taxes) {
                        const rate = tax.amount || 0;
                        const label = rate === 0 ? "GST Exempt" : `GST @ ${rate}%`;
                        if (!taxGroups[label]) {
                            taxGroups[label] = { taxable: 0, gst: 0, rate: rate };
                        }
                        taxGroups[label].taxable += line.price_subtotal || 0;
                        taxGroups[label].gst += (line.price_subtotal || 0) * (rate / 100);
                    }
                }
            }
        }

        const fmt = (v) => v.toFixed(2);

        return Object.entries(taxGroups).map(([label, data]) => {
            const halfGst = data.gst / 2;
            return {
                rate: label,
                taxable: fmt(data.taxable),
                cgst: fmt(halfGst),
                sgst: fmt(halfGst),
            };
        });
    },

    getGstTotals() {
        const rows = this.getGstRows();
        const totals = rows.reduce(
            (acc, row) => {
                acc.taxable += parseFloat(row.taxable);
                acc.cgst += parseFloat(row.cgst);
                acc.sgst += parseFloat(row.sgst);
                return acc;
            },
            { taxable: 0, cgst: 0, sgst: 0 }
        );
        return {
            taxable: totals.taxable.toFixed(2),
            cgst: totals.cgst.toFixed(2),
            sgst: totals.sgst.toFixed(2),
        };
    },
});