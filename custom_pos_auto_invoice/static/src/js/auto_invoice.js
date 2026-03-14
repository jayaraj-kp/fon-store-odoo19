/** @odoo-module **/

/**
 * custom_pos_auto_invoice/static/src/js/auto_invoice.js
 *
 * WHY WE PATCH OrderPaymentValidation (not PaymentScreen):
 * ─────────────────────────────────────────────────────────
 * The one-click fast payment buttons on the product screen call:
 *   ProductScreen.fastValidate(paymentMethod)
 *     → pos_store.validateOrderFast(paymentMethod)
 *       → new OrderPaymentValidation({ fastPaymentMethod })
 *         → validation.validateOrder()
 *
 * The normal Payment Screen also calls:
 *   PaymentScreen.validateOrder()
 *     → new OrderPaymentValidation({})
 *       → validation.validateOrder()
 *
 * Both paths go through OrderPaymentValidation.validateOrder().
 * Patching it here fixes BOTH payment flows at once.
 *
 * IMPORTANT RULE (from reading the source):
 * ──────────────────────────────────────────
 * In isOrderValid(), if to_invoice = true but no partner is set,
 * Odoo shows a "Please select the Customer" dialog and BLOCKS the order.
 * So we only set to_invoice = true when a partner exists.
 */

import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";

// Save reference to original validateOrder
const _originalValidateOrder = OrderPaymentValidation.prototype.validateOrder;

OrderPaymentValidation.prototype.validateOrder = async function (isForceValidate) {
    const order = this.order;

    if (order) {
        const partner = order.getPartner ? order.getPartner() : order.partner_id;

        if (partner) {
            // Customer is set — safe to request invoice
            order.to_invoice = true;
        }
        // No partner → leave to_invoice as-is (don't set true, avoids the
        // "Please select the Customer" blocking dialog from isOrderValid)
    }

    return await _originalValidateOrder.call(this, isForceValidate);
};

/**
 * Disable automatic invoice PDF download/print after payment.
 * The invoice is still CREATED in the background (to_invoice = true),
 * but the PDF will NOT be automatically downloaded or printed.
 * Cashier can print it manually from the Invoices screen.
 */
OrderPaymentValidation.prototype.shouldDownloadInvoice = function () {
    return false;
};
