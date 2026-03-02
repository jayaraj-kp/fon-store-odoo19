/** @odoo-module **/

import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { patch } from "@web/core/utils/patch";
import { onMounted, onPatched } from "@odoo/owl";

patch(OrderReceipt.prototype, {
    setup() {
        super.setup(...arguments);
        onMounted(() => this._injectGstTable());
        onPatched(() => this._injectGstTable());
    },

    _getGstData() {
        const order = this.props.data;
        const groups = {};

        if (order && order.orderlines) {
            for (const line of order.orderlines) {
                if (!line.taxes || line.taxes.length === 0) {
                    groups["GST Exempt"] = groups["GST Exempt"] || { taxable: 0, gst: 0 };
                    groups["GST Exempt"].taxable += line.price_subtotal || 0;
                } else {
                    for (const tax of line.taxes) {
                        const rate = tax.amount || 0;
                        const label = rate === 0 ? "GST Exempt" : `GST @ ${rate}%`;
                        groups[label] = groups[label] || { taxable: 0, gst: 0 };
                        groups[label].taxable += line.price_subtotal || 0;
                        groups[label].gst += (line.price_subtotal || 0) * (rate / 100);
                    }
                }
            }
        }

        const fmt = (v) => (v || 0).toFixed(2);
        const rows = Object.entries(groups).map(([label, d]) => ({
            rate: label,
            taxable: fmt(d.taxable),
            cgst: fmt(d.gst / 2),
            sgst: fmt(d.gst / 2),
        }));

        const totals = rows.reduce(
            (acc, r) => ({
                taxable: acc.taxable + parseFloat(r.taxable),
                cgst: acc.cgst + parseFloat(r.cgst),
                sgst: acc.sgst + parseFloat(r.sgst),
            }),
            { taxable: 0, cgst: 0, sgst: 0 }
        );

        return { rows, totals };
    },

    _injectGstTable() {
        // Find the QR code container
        const el = this.__owl__.bdom && this.__owl__.bdom.el
            ? this.__owl__.bdom.el
            : document.querySelector(".pos-receipt");

        if (!el) return;

        const qrDiv = el.querySelector(".pos-receipt-qrcode");
        if (!qrDiv || qrDiv.dataset.gstInjected) return;

        qrDiv.dataset.gstInjected = "1";

        // Shrink the QR image inside
        const qrImg = qrDiv.querySelector("img, canvas");
        if (qrImg) {
            qrImg.style.width = "80px";
            qrImg.style.height = "80px";
        }

        // Build GST table
        const { rows, totals } = this._getGstData();
        const fmt = (v) => parseFloat(v).toFixed(2);

        let tbodyHtml = rows.map(r => `
            <tr>
                <td>${r.rate}</td>
                <td class="gst-amt">${r.taxable}</td>
                <td class="gst-amt">${r.cgst}</td>
                <td class="gst-amt">${r.sgst}</td>
            </tr>
        `).join("");

        const tableHtml = `
            <div class="gst-summary-table">
                <table>
                    <thead>
                        <tr>
                            <th>GST Rate</th>
                            <th>Taxable</th>
                            <th>CGST</th>
                            <th>SGST</th>
                        </tr>
                    </thead>
                    <tbody>${tbodyHtml}</tbody>
                    <tfoot>
                        <tr>
                            <td><b>Total</b></td>
                            <td class="gst-amt"><b>${fmt(totals.taxable)}</b></td>
                            <td class="gst-amt"><b>${fmt(totals.cgst)}</b></td>
                            <td class="gst-amt"><b>${fmt(totals.sgst)}</b></td>
                        </tr>
                    </tfoot>
                </table>
            </div>
        `;

        // Wrap QR + Table in a flex row
        const wrapper = document.createElement("div");
        wrapper.className = "gst-qr-wrapper";
        qrDiv.parentNode.insertBefore(wrapper, qrDiv);
        wrapper.appendChild(qrDiv);
        wrapper.insertAdjacentHTML("beforeend", tableHtml);
    },
});