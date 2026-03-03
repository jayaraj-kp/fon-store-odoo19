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

    // DEBUG - find the correct amount path
    console.log('[UPI DEBUG] props:', JSON.stringify(Object.keys(this.props || {})));
    console.log('[UPI DEBUG] props.info:', JSON.stringify(this.props?.info));
    console.log('[UPI DEBUG] total_with_tax:', this.props?.info?.total_with_tax);
    console.log('[UPI DEBUG] amount_total:', this.props?.info?.amount_total);
    console.log('[UPI DEBUG] total:', this.props?.info?.total);

    const amount = (
        this.props?.info?.total_with_tax ??
        this.props?.info?.amount_total ??
        this.props?.info?.total ??
        0
    ).toFixed(2);

    console.log('[UPI DEBUG] final amount:', amount);

    const vpa  = encodeURIComponent(config.upi_vpa.trim());
    const name = encodeURIComponent((config.upi_merchant_name || config.name || 'Store').trim());
    const note = encodeURIComponent('POS Payment');

    return `/pos/upi_qr?vpa=${vpa}&name=${name}&amount=${amount}&note=${note}`;
},