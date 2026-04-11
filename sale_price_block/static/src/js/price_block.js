///** @odoo-module **/
//
//import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
//import { patch } from "@web/core/utils/patch";
//import { _t } from "@web/core/l10n/translation";
//
///**
// * Patch PaymentScreen to add below-cost price validation
// * Blocks payment if any product is sold below its cost price
// * Uses unified 'sale_price_block.block_below_cost' setting
// */
//patch(PaymentScreen.prototype, {
//    async validateOrderBeforePayment() {
//        const order = this.pos.get_order();
//
//        if (!order) {
//            return true;
//        }
//
//        // Check if any order line has a price below cost
//        const belowCostLines = [];
//
//        order.get_orderlines().forEach((line) => {
//            const product = line.get_product();
//            if (product) {
//                const costPrice = product.standard_price || 0.0;
//                const salePrice = line.price_unit || 0.0;
//
//                if (salePrice < costPrice) {
//                    belowCostLines.push({
//                        name: product.display_name,
//                        salePrice: salePrice,
//                        costPrice: costPrice,
//                        symbol: this.pos.currency.symbol,
//                    });
//                }
//            }
//        });
//
//        // If below-cost items found, show error dialog
//        if (belowCostLines.length > 0) {
//            let message = _t("Cannot process this order.\n\n");
//            message += _t("The following product(s) have a unit price BELOW their cost price:\n\n");
//
//            belowCostLines.forEach((item) => {
//                message += `• ${item.name}  →  Sale Price: ${item.symbol} ${item.salePrice.toFixed(2)}  |  Cost Price: ${item.symbol} ${item.costPrice.toFixed(2)}\n`;
//            });
//
//            message += _t("\n\nPlease adjust the sale prices before proceeding to payment.");
//
//            // Show error dialog
//            await this.showPopup("ErrorPopup", {
//                title: _t("Invalid Order"),
//                body: message,
//            });
//
//            return false;
//        }
//
//        return true;
//    },
//
//    async validateAndProceed() {
//        // Validate before allowing payment
//        const isValid = await this.validateOrderBeforePayment();
//
//        if (!isValid) {
//            return; // Block payment
//        }
//
//        // If valid, proceed with original flow
//        return this._super();
//    }
//});
//
///**
// * Additional patch to intercept the payment button click
// * This provides an extra layer of protection
// */
//patch(PaymentScreen.prototype, {
//    async handlePaymentButtonClick() {
//        const isValid = await this.validateOrderBeforePayment();
//
//        if (!isValid) {
//            return; // Don't proceed with payment
//        }
//
//        // Call original handler if validation passed
//        return this._super();
//    }
//});
/** @odoo-module **/
/** @odoo-module **/

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

/**
 * SIMPLE APPROACH: Validate only when payment is actually being processed
 * This ensures payment buttons remain responsive while validation happens
 */

patch(PaymentScreen.prototype, {
    /**
     * Check if order has items below cost price
     */
    getOrderBelowCostItems() {
        const order = this.pos.get_order();
        const belowCostLines = [];

        if (!order) return belowCostLines;

        (order.get_orderlines() || []).forEach((line) => {
            if (!line.get_product()) return;

            const product = line.get_product();
            const cost = product.standard_price || 0;
            const price = line.price_unit || 0;

            if (price < cost) {
                belowCostLines.push({
                    name: product.display_name,
                    price: price,
                    cost: cost,
                    symbol: this.pos.currency.symbol || '$'
                });
            }
        });

        return belowCostLines;
    },

    /**
     * Build error message from below-cost items
     */
    buildErrorMessage(items) {
        if (!items || items.length === 0) return '';

        let msg = _t("Cannot process this order.\n\n");
        msg += _t("The following product(s) have a unit price BELOW their cost price:\n\n");

        items.forEach((item) => {
            msg += `• ${item.name}  →  `;
            msg += `Sale Price: ${item.symbol} ${item.price.toFixed(2)}  |  `;
            msg += `Cost Price: ${item.symbol} ${item.cost.toFixed(2)}\n`;
        });

        msg += _t("\n\nPlease adjust the sale prices before proceeding to payment.");
        return msg;
    },

    /**
     * Intercept payment submission
     * This is called right before payment is processed
     */
    async validateAndProcessPayment() {
        const belowCostItems = this.getOrderBelowCostItems();

        if (belowCostItems.length > 0) {
            const errorMsg = this.buildErrorMessage(belowCostItems);

            await this.showPopup("ErrorPopup", {
                title: _t("Invalid Order"),
                body: errorMsg,
            });

            // Return false to prevent payment
            return false;
        }

        // Payment is valid, allow it to proceed
        return true;
    },

    /**
     * Override the main payment processing
     * This ensures validation happens at the right time
     */
    async _processPayment() {
        const isValid = await this.validateAndProcessPayment();

        if (!isValid) {
            return; // Block payment
        }

        // Proceed with parent method
        return this._super();
    }
});

/**
 * Override pay button processing
 * This is a safer approach that intercepts at the pay button level
 */
patch(PaymentScreen.prototype, {
    async onClickPay() {
        const belowCostItems = this.getOrderBelowCostItems();

        if (belowCostItems.length > 0) {
            const errorMsg = this.buildErrorMessage(belowCostItems);

            await this.showPopup("ErrorPopup", {
                title: _t("Invalid Order"),
                body: errorMsg,
            });

            // Return to prevent payment
            return false;
        }

        // Valid order, proceed with parent
        return this._super();
    }
});