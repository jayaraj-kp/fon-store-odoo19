/** @odoo-module */

console.log("[sale_price_block] Loading - simple event-based approach");

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

/**
 * Simple helper to check for below-cost items
 */
function checkBelowCostItems(order) {
    if (!order?.lines) return { hasBelowCost: false, message: "" };

    const issues = [];

    for (const line of order.lines) {
        if (!line.product_id) continue;

        const costPrice = line.product_id.standard_price || 0;
        const salePrice = line.price_unit || 0;

        if (salePrice < costPrice) {
            issues.push({
                product: line.product_id.display_name,
                salePrice,
                costPrice
            });
        }
    }

    if (issues.length === 0) {
        return { hasBelowCost: false, message: "" };
    }

    let message = "Cannot process this order.\n\n";
    message += "The following product(s) have a unit price BELOW their cost price:\n\n";

    issues.forEach(issue => {
        message += `• ${issue.product}\n`;
        message += `  Sale Price: ₹ ${issue.salePrice.toFixed(2)}\n`;
        message += `  Cost Price: ₹ ${issue.costPrice.toFixed(2)}\n\n`;
    });

    message += "Please update the sale prices before proceeding to payment.";

    return { hasBelowCost: true, message };
}

/**
 * Main patch for PaymentScreen
 */
patch(PaymentScreen.prototype, {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
        console.log("[sale_price_block] PaymentScreen patched");
    },

    /**
     * Override validateOrder - the main payment validation
     */
    async validateOrder(isForceValidate) {
        // Get the order
        const order = this.pos?.pendingOrder;

        // Check for below-cost items
        const { hasBelowCost, message } = checkBelowCostItems(order);

        if (hasBelowCost) {
            console.log("[sale_price_block] Order blocked - below cost items found");

            // Show error dialog
            await this.dialog.add(window.ErrorDialog || window.AlertDialog, {
                title: "Invalid Order",
                body: message,
            });

            return; // Block payment
        }

        // If validation passes, continue with original method
        console.log("[sale_price_block] Validation passed - proceeding with payment");
        return super.validateOrder?.(isForceValidate);
    },

    /**
     * Also override other payment-related methods
     */
    async validateOrderFast() {
        const order = this.pos?.pendingOrder;
        const { hasBelowCost, message } = checkBelowCostItems(order);

        if (hasBelowCost) {
            await this.dialog.add(window.ErrorDialog || window.AlertDialog, {
                title: "Invalid Order",
                body: message,
            });
            return;
        }

        return super.validateOrderFast?.();
    },

    async addPaymentLine(paymentMethod) {
        const order = this.pos?.pendingOrder;
        const { hasBelowCost, message } = checkBelowCostItems(order);

        if (hasBelowCost) {
            await this.dialog.add(window.ErrorDialog || window.AlertDialog, {
                title: "Invalid Order",
                body: message,
            });
            return;
        }

        return super.addPaymentLine?.(paymentMethod);
    },

    async addPayment(paymentMethod) {
        const order = this.pos?.pendingOrder;
        const { hasBelowCost, message } = checkBelowCostItems(order);

        if (hasBelowCost) {
            await this.dialog.add(window.ErrorDialog || window.AlertDialog, {
                title: "Invalid Order",
                body: message,
            });
            return;
        }

        return super.addPayment?.(paymentMethod);
    },
});

window.__pb_loaded = true;
console.log("[sale_price_block] Setup complete!");