/** @odoo-module **/

import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { patch } from "@web/core/utils/patch";
import { Component } from "@odoo/owl";

export class GstTableSection extends Component {
    static template = "pos_receipt_custom.GstTableSection";

    get gstRows() {
        const order = this.props.data;
        const taxGroups = {};

        if (order && order.orderlines) {
            for (const line of order.orderlines) {
                if (!line.taxes || line.taxes.length === 0) {
                    if (!taxGroups["GST Exempt"]) {
                        taxGroups["GST Exempt"] = { taxable: 0, gst: 0, rate: 0 };
                    }
                    taxGroups["GST Exempt"].taxable += line.price_subtotal || 0;
                } else {
                    for (const tax of line.taxes) {
                        const rate = tax.amount || 0;
                        const label = rate === 0 ? "GST Exempt" : `GST @ ${rate}%`;
                        if (!taxGroups[label]) {
                            taxGroups[label] = { taxable: 0, gst: 0, rate };
                        }
                        taxGroups[label].taxable += line.price_subtotal || 0;
                        taxGroups[label].gst += (line.price_subtotal || 0) * (rate / 100);
                    }
                }
            }
        }

        const fmt = (v) => (v || 0).toFixed(2);
        return Object.entries(taxGroups).map(([label, data]) => ({
            rate: label,
            taxable: fmt(data.taxable),
            cgst: fmt(data.gst / 2),
            sgst: fmt(data.gst / 2),
        }));
    }

    get gstTotals() {
        const rows = this.gstRows;
        const t = rows.reduce(
            (acc, r) => {
                acc.taxable += parseFloat(r.taxable);
                acc.cgst += parseFloat(r.cgst);
                acc.sgst += parseFloat(r.sgst);
                return acc;
            },
            { taxable: 0, cgst: 0, sgst: 0 }
        );
        return {
            taxable: t.taxable.toFixed(2),
            cgst: t.cgst.toFixed(2),
            sgst: t.sgst.toFixed(2),
        };
    }
}

patch(OrderReceipt, {
    components: {
        ...OrderReceipt.components,
        GstTableSection,
    },
});