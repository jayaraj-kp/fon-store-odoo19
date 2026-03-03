/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";

patch(OrderReceipt.prototype, {

    get upiQrSrc() {
        const config = this.pos?.config
                    || this.env?.services?.pos?.config
                    || this.env?.pos?.config;

        if (!config || !config.upi_qr_on_receipt || !config.upi_vpa) {
            return null;
        }

        // Odoo 19: amount lives in props.order, not props.info
        const order = this.props?.order;
        const amount = (
            order?.get_total_with_tax?.() ??
            order?.amount_total ??
            order?.total_with_tax ??
            0
        ).toFixed(2);

        const vpa  = encodeURIComponent(config.upi_vpa.trim());
        const name = encodeURIComponent(
            (config.upi_merchant_name || config.name || 'Store').trim()
        );
        const note = encodeURIComponent('POS Payment');

        return `/pos/upi_qr?vpa=${vpa}&name=${name}&amount=${amount}&note=${note}`;
    },

    get upiAmount() {
        const order = this.props?.order;
        const amount = (
            order?.get_total_with_tax?.() ??
            order?.amount_total ??
            order?.total_with_tax ??
            0
        );
        return Number(amount).toFixed(2);
    },

    get upiVpa() {
        const config = this.pos?.config
                    || this.env?.services?.pos?.config
                    || this.env?.pos?.config;
        return config?.upi_vpa || '';
    },
});