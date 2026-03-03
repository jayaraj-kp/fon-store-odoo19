/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";

patch(OrderReceipt.prototype, {

    get upiQrSrc() {
        // Try multiple ways to access config in Odoo 19
        const config = this.pos?.config
                    || this.env?.services?.pos?.config
                    || this.env?.pos?.config;

        console.log('[UPI DEBUG] config:', config);
        console.log('[UPI DEBUG] upi_qr_on_receipt:', config?.upi_qr_on_receipt);
        console.log('[UPI DEBUG] upi_vpa:', config?.upi_vpa);

        if (!config || !config.upi_qr_on_receipt || !config.upi_vpa) {
            return null;
        }

        const amount = (this.props?.info?.total_with_tax ?? 0).toFixed(2);
        const vpa    = encodeURIComponent(config.upi_vpa.trim());
        const name   = encodeURIComponent(
            (config.upi_merchant_name || config.name || 'Store').trim()
        );
        const note   = encodeURIComponent('POS Payment');

        return `/pos/upi_qr?vpa=${vpa}&name=${name}&amount=${amount}&note=${note}`;
    },

    get upiAmount() {
        const amount = this.props?.info?.total_with_tax ?? 0;
        return amount.toFixed(2);
    },

    get upiVpa() {
        const config = this.pos?.config
                    || this.env?.services?.pos?.config
                    || this.env?.pos?.config;
        return config?.upi_vpa || '';
    },
});