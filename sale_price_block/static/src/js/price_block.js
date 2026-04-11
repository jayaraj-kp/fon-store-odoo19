/** @odoo-module */

console.log("[sale_price_block] JavaScript-only price validation loaded");

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

/**
 * Check if any order line has price below cost
 */
function hasBelowCostPrice(order) {
    if (!order || !order.lines) return false;

    for (const line of order.lines) {
        if (!line.product_id) continue;

        const costPrice = line.product_id.standard_price || 0;
        const salePrice = line.price_unit || 0;

        if (salePrice < costPrice) {
            return true;
        }
    }

    return false;
}

/**
 * Get error message with details
 */
function getErrorMessage(order) {
    if (!order || !order.lines) return "";

    const belowCostItems = [];

    for (const line of order.lines) {
        if (!line.product_id) continue;

        const costPrice = line.product_id.standard_price || 0;
        const salePrice = line.price_unit || 0;

        if (salePrice < costPrice) {
            belowCostItems.push({
                name: line.product_id.display_name,
                salePrice: salePrice,
                costPrice: costPrice,
            });
        }
    }

    if (belowCostItems.length === 0) return "";

    let message = "The following product(s) have a unit price BELOW their cost price:\n\n";

    belowCostItems.forEach((item) => {
        message += `• ${item.name}\n`;
        message += `  Sale Price: ₹ ${item.salePrice.toFixed(2)}\n`;
        message += `  Cost Price: ₹ ${item.costPrice.toFixed(2)}\n\n`;
    });

    message += "Please update the sale prices before proceeding to payment.";

    return message;
}

/**
 * Patch PaymentScreen to validate prices
 */
patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
        console.log("[sale_price_block] PaymentScreen validation active");
    },

    /**
     * Validate order before payment
     */
    async validateOrder(isForceValidate) {
        const order = this.pos.pendingOrder;

        if (hasBelowCostPrice(order)) {
            const message = getErrorMessage(order);

            await this.dialog.add(window.ErrorDialog || window.AlertDialog, {
                title: "Cannot Process Order",
                body: message,
                buttons: [{ text: "OK" }],
            });

            console.log("[sale_price_block] Order blocked - below cost items found");
            return;
        }

        console.log("[sale_price_block] Order validation passed");
        return super.validateOrder?.(...arguments);
    },

    /**
     * Fast validation
     */
    async validateOrderFast() {
        const order = this.pos.pendingOrder;

        if (hasBelowCostPrice(order)) {
            const message = getErrorMessage(order);

            await this.dialog.add(window.ErrorDialog || window.AlertDialog, {
                title: "Cannot Process Order",
                body: message,
                buttons: [{ text: "OK" }],
            });

            return;
        }

        return super.validateOrderFast?.(...arguments);
    },

    /**
     * Add payment line
     */
    async addPaymentLine(paymentMethod) {
        const order = this.pos.pendingOrder;

        if (hasBelowCostPrice(order)) {
            const message = getErrorMessage(order);

            await this.dialog.add(window.ErrorDialog || window.AlertDialog, {
                title: "Cannot Process Order",
                body: message,
                buttons: [{ text: "OK" }],
            });

            return;
        }

        return super.addPaymentLine?.(...arguments);
    },

    /**
     * Add payment
     */
    async addPayment(paymentMethod) {
        const order = this.pos.pendingOrder;

        if (hasBelowCostPrice(order)) {
            const message = getErrorMessage(order);

            await this.dialog.add(window.ErrorDialog || window.AlertDialog, {
                title: "Cannot Process Order",
                body: message,
                buttons: [{ text: "OK" }],
            });

            return;
        }

        return super.addPayment?.(...arguments);
    },
});

console.log("[sale_price_block] Setup complete - Price validation ready");