/** @odoo-module */

console.log("[sale_price_block] Price validation v19 loaded");

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

/**
 * Check if any order line has price below cost
 */
function hasBelowCostPrice(pos) {
    try {
        // Get the order - try multiple ways like require_customer does
        const order = pos?.pendingOrder || pos?.get_order?.() || pos?.currentOrder;

        if (!order || !order.lines) return false;

        // Check each line
        for (const line of order.lines) {
            if (!line.product_id) continue;

            const costPrice = line.product_id.standard_price || 0;
            const salePrice = line.price_unit || 0;

            if (salePrice < costPrice) {
                return true; // Found at least one below-cost item
            }
        }

        return false;
    } catch (e) {
        console.warn("[sale_price_block] price check error:", e);
        return false;
    }
}

/**
 * Get detailed error message
 */
function getBelowCostErrorMessage(pos) {
    try {
        const order = pos?.pendingOrder || pos?.get_order?.() || pos?.currentOrder;
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
                    symbol: pos.currency?.symbol || '$'
                });
            }
        }

        if (belowCostItems.length === 0) return "";

        let message = "The following product(s) have a unit price BELOW their cost price:\n\n";

        belowCostItems.forEach((item) => {
            message += `• ${item.name}\n`;
            message += `  Sale Price: ${item.symbol} ${item.salePrice.toFixed(2)}\n`;
            message += `  Cost Price: ${item.symbol} ${item.costPrice.toFixed(2)}\n\n`;
        });

        message += "Please update the sale prices before proceeding to payment.";

        return message;
    } catch (e) {
        console.warn("[sale_price_block] error message generation:", e);
        return "";
    }
}

/**
 * Show error dialog
 */
async function showErrorDialog(dialogService, message) {
    return new Promise((resolve) => {
        dialogService.add(window.ErrorDialog || window.AlertDialog, {
            title: "Invalid Order",
            body: message,
            buttons: [{ text: "OK", click: resolve }],
        });
    });
}

// Patch PaymentScreen - the key to fixing payment buttons
patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this._priceBlockDialog = useService("dialog");
        console.log("[sale_price_block] PaymentScreen setup");
    },

    // Intercept order validation
    async validateOrder(isForceValidate) {
        if (hasBelowCostPrice(this.pos)) {
            const message = getBelowCostErrorMessage(this.pos);
            await this._priceBlockDialog.add(window.ErrorDialog || window.AlertDialog, {
                title: "Invalid Order",
                body: message,
                buttons: [{ text: "OK" }],
            });
            return;
        }
        return super.validateOrder?.(...arguments);
    },

    // Intercept fast validation
    async validateOrderFast() {
        if (hasBelowCostPrice(this.pos)) {
            const message = getBelowCostErrorMessage(this.pos);
            await this._priceBlockDialog.add(window.ErrorDialog || window.ErrorDialog, {
                title: "Invalid Order",
                body: message,
                buttons: [{ text: "OK" }],
            });
            return;
        }
        return super.validateOrderFast?.(...arguments);
    },

    // Intercept payment line addition
    async addPaymentLine(paymentMethod) {
        if (hasBelowCostPrice(this.pos)) {
            const message = getBelowCostErrorMessage(this.pos);
            await this._priceBlockDialog.add(window.ErrorDialog || window.AlertDialog, {
                title: "Invalid Order",
                body: message,
                buttons: [{ text: "OK" }],
            });
            return;
        }
        return super.addPaymentLine?.(...arguments);
    },

    // Intercept payment addition
    async addPayment(paymentMethod) {
        if (hasBelowCostPrice(this.pos)) {
            const message = getBelowCostErrorMessage(this.pos);
            await this._priceBlockDialog.add(window.ErrorDialog || window.AlertDialog, {
                title: "Invalid Order",
                body: message,
                buttons: [{ text: "OK" }],
            });
            return;
        }
        return super.addPayment?.(...arguments);
    },
});

// Also patch the pos model directly (like require_customer does)
if (window.posmodel && !window.posmodel.__pb_wrapped__) {
    const origPay = window.posmodel.pay?.bind(window.posmodel);
    const origValidate = window.posmodel.validateOrderFast?.bind(window.posmodel);

    if (origPay) {
        window.posmodel.pay = async function(...args) {
            if (hasBelowCostPrice(this)) {
                console.log("[sale_price_block] Blocking payment - below cost items found");
                // Payment should be blocked by backend error anyway
                return origPay(...args);
            }
            return origPay(...args);
        };
    }

    if (origValidate) {
        window.posmodel.validateOrderFast = async function(...args) {
            if (hasBelowCostPrice(this)) {
                console.log("[sale_price_block] Fast validation blocked - below cost items");
                return false;
            }
            return origValidate(...args);
        };
    }

    window.posmodel.__pb_wrapped__ = true;
}

console.log("[sale_price_block] Setup complete - price validation active");