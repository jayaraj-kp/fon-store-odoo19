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

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

/**
 * Unified Price Block - POS Payment Validation
 *
 * Validates order before payment is processed.
 * If validation fails, shows error and allows user to fix prices.
 * Once prices are fixed, payment buttons work normally.
 */

let originalConfirmPayment = null;

patch(PaymentScreen.prototype, {
    setup() {
        this._super();

        // Store the original confirm payment method
        if (!originalConfirmPayment && this.confirmPayment) {
            originalConfirmPayment = this.confirmPayment.bind(this);
        }
    },

    /**
     * Validate order before allowing payment
     * Returns {valid: boolean, message: string}
     */
    validateOrderPrices() {
        const order = this.pos.get_order();

        if (!order || !order.get_orderlines()) {
            return { valid: true, message: '' };
        }

        const belowCostLines = [];

        // Check each order line for below-cost pricing
        order.get_orderlines().forEach((line) => {
            const product = line.get_product();
            if (product) {
                const costPrice = product.standard_price || 0.0;
                const salePrice = line.price_unit || 0.0;

                if (salePrice < costPrice) {
                    belowCostLines.push({
                        name: product.display_name,
                        salePrice: salePrice,
                        costPrice: costPrice,
                        symbol: this.pos.currency.symbol || '$',
                    });
                }
            }
        });

        if (belowCostLines.length > 0) {
            let message = _t("Cannot process this order.\n\n");
            message += _t("The following product(s) have a unit price BELOW their cost price:\n\n");

            belowCostLines.forEach((item) => {
                const sp = item.salePrice.toFixed(2);
                const cp = item.costPrice.toFixed(2);
                message += `• ${item.name}  →  Sale Price: ${item.symbol} ${sp}  |  Cost Price: ${item.symbol} ${cp}\n`;
            });

            message += _t("\n\nPlease adjust the sale prices before proceeding to payment.");

            return {
                valid: false,
                message: message,
                items: belowCostLines
            };
        }

        return { valid: true, message: '' };
    },

    /**
     * Override the confirm payment method
     * This is called when payment button (Cash, Card, etc.) is clicked
     */
    async confirmPayment() {
        // Validate prices BEFORE proceeding
        const validation = this.validateOrderPrices();

        if (!validation.valid) {
            // Show error popup and block payment
            await this.showPopup("ErrorPopup", {
                title: _t("Invalid Order"),
                body: validation.message,
            });

            // Don't proceed with payment - return early
            return false;
        }

        // If validation passes, proceed with original payment flow
        if (originalConfirmPayment) {
            return await originalConfirmPayment();
        }

        // Fallback to parent method if original not stored
        return await this._super();
    }
});

/**
 * Additional patch for payment method buttons
 * Some versions call different methods for payment
 */
patch(PaymentScreen.prototype, {
    async onClickPaymentMethod(paymentMethod) {
        // Validate before payment method selection
        const validation = this.validateOrderPrices();

        if (!validation.valid) {
            await this.showPopup("ErrorPopup", {
                title: _t("Invalid Order"),
                body: validation.message,
            });
            return false;
        }

        // If valid, proceed with payment method
        return await this._super();
    }
});

/**
 * Patch for when order is submitted/confirmed
 */
patch(PaymentScreen.prototype, {
    async submitOrder() {
        const validation = this.validateOrderPrices();

        if (!validation.valid) {
            await this.showPopup("ErrorPopup", {
                title: _t("Invalid Order"),
                body: validation.message,
            });
            return false;
        }

        return await this._super();
    }
});