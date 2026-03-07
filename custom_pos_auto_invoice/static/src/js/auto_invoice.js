/** @odoo-module **/

/**
 * custom_pos_auto_invoice/auto_invoice.js
 *
 * Patches the POS PaymentScreen so that every time the operator
 * clicks "Validate" (regardless of payment method – Cash, Card, etc.)
 * the order is automatically flagged as to_invoice = true.
 *
 * This triggers Odoo's standard invoice-creation flow:
 *   1. The receipt is printed as usual.
 *   2. An accounting Invoice (INV/…) is created and linked to the order.
 *   3. If your custom_pos_receipt module is installed, the receipt
 *      already picks up the invoice number via order.account_move?.name.
 *
 * No UI changes are made — it's fully transparent to the cashier.
 */

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {

    // ------------------------------------------------------------------
    // validateOrder — called when cashier presses the green Validate btn
    // ------------------------------------------------------------------
    async validateOrder(isForceValidate) {

        const order = this.currentOrder;

        if (order) {
            // ① Always request invoice
            order.to_invoice = true;

            // ② If no customer is set, try to fall back to the POS
            //    default partner (configured in POS Settings → Customers).
            //    Without a partner Odoo cannot create a proper invoice.
            if (!order.partner_id) {
                const defaultPartner =
                    this.pos.config.default_partner_id ||   // Odoo 17+
                    this.pos.config.partner_id ||
                    null;

                if (defaultPartner) {
                    order.set_partner(defaultPartner);
                }
                // If still no partner, Odoo will silently skip invoice
                // creation (standard behaviour) — no crash.
            }
        }

        // Delegate to the original PaymentScreen.validateOrder
        return await super.validateOrder(isForceValidate);
    },

    // ------------------------------------------------------------------
    // _handleFinalizedOrder — runs right after the server confirms the
    //   order. We use it to ensure the UI "invoice" checkbox stays ON
    //   in case anything reset it between our patch and Odoo's check.
    // ------------------------------------------------------------------
    async _handleFinalizedOrder(order) {
        if (order) {
            order.to_invoice = true;
        }
        return await super._handleFinalizedOrder(order);
    },
});
