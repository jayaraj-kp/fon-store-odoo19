/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";

/**
 * Patch the OrderReceipt component to expose a computed UPI QR image URL.
 *
 * The URL points to our Odoo controller /pos/upi_qr which returns a PNG.
 * The PNG is generated server-side using Python's `qrcode` library with
 * the UPI deep-link format:
 *   upi://pay?pa=<VPA>&pn=<Name>&am=<Amount>&cu=INR&tn=POS+Payment
 */
patch(OrderReceipt.prototype, {

    /**
     * Returns the src URL for the UPI QR image, or null if UPI is not configured.
     * Called by the OWL template on every render.
     */
    get upiQrSrc() {
        const config = this.pos?.config;
        if (!config || !config.upi_qr_on_receipt || !config.upi_vpa) {
            return null;
        }

        // Grand total from receipt info (already rounded to 2 dp by Odoo)
        const amount = (this.props?.info?.total_with_tax ?? 0).toFixed(2);
        const vpa    = encodeURIComponent(config.upi_vpa.trim());
        const name   = encodeURIComponent(
            (config.upi_merchant_name || config.name || 'Store').trim()
        );
        const note   = encodeURIComponent('POS Payment');

        return `/pos/upi_qr?vpa=${vpa}&name=${name}&amount=${amount}&note=${note}`;
    },

    /**
     * Helper used in template to display the formatted amount.
     */
    get upiAmount() {
        const amount = this.props?.info?.total_with_tax ?? 0;
        return amount.toFixed(2);
    },

    /**
     * The configured UPI VPA, exposed for the template label.
     */
    get upiVpa() {
        return this.pos?.config?.upi_vpa || '';
    },
});
