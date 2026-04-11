/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

/**
 * ODOO 19 POS - CORRECT IMPLEMENTATION
 *
 * Key difference: Uses posmodel.pendingOrder instead of get_order()
 * which is the way Odoo 19 POS stores the current order
 */

// We need to patch the POS model to add our validation
patch(Object.getPrototypeOf(window.posmodel), {
    /**
     * Validate if current order has any items below cost price
     * Returns: {valid: boolean, message: string, items: array}
     */
    validatePricesBeforePayment() {
        const order = this.pendingOrder;

        if (!order || !order.lines) {
            return { valid: true, message: '', items: [] };
        }

        const belowCostLines = [];

        // Check each line in the order
        order.lines.forEach((line) => {
            if (!line.product_id) return;

            const product = line.product_id;
            const costPrice = product.standard_price || 0;
            const salePrice = line.price_unit || 0;

            if (salePrice < costPrice) {
                belowCostLines.push({
                    name: product.display_name,
                    salePrice: salePrice,
                    costPrice: costPrice,
                    symbol: this.currency?.symbol || '$',
                });
            }
        });

        if (belowCostLines.length > 0) {
            let message = _t("Cannot process this order.\n\n");
            message += _t("The following product(s) have a unit price BELOW their cost price:\n\n");

            belowCostLines.forEach((item) => {
                message += `• ${item.name}  →  `;
                message += `Sale Price: ${item.symbol} ${item.salePrice.toFixed(2)}  |  `;
                message += `Cost Price: ${item.symbol} ${item.costPrice.toFixed(2)}\n`;
            });

            message += _t("\n\nPlease adjust the sale prices before proceeding to payment.");

            return {
                valid: false,
                message: message,
                items: belowCostLines
            };
        }

        return { valid: true, message: '', items: [] };
    }
});

/**
 * Patch the pay() method in posmodel
 * This is called when user clicks any payment button
 */
patch(window.posmodel, {
    async pay() {
        // Validate prices before payment
        const validation = this.validatePricesBeforePayment();

        if (!validation.valid) {
            // Show error dialog
            await this.dialog.add({
                body: validation.message,
                title: _t("Invalid Order"),
                buttons: [
                    { text: _t("OK"), click: () => true }
                ]
            });

            // Block payment
            return;
        }

        // If validation passes, proceed with original payment
        return this._super();
    }
});

/**
 * Also patch validateOrderFast() which might be used for quick validation
 */
patch(window.posmodel, {
    async validateOrderFast() {
        // Quick validation for below-cost items
        const validation = this.validatePricesBeforePayment();

        if (!validation.valid) {
            await this.dialog.add({
                body: validation.message,
                title: _t("Invalid Order"),
                buttons: [
                    { text: _t("OK"), click: () => true }
                ]
            });
            return false;
        }

        // If validation passes, proceed with original method
        return this._super();
    }
});