/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

/**
 * Checks all order lines for price-below-cost violations.
 * Returns list of violation objects or empty array.
 */
function getViolations(order, products) {
    const violations = [];
    if (!order) return violations;

    for (const line of order.get_orderlines()) {
        const product = line.product;
        if (!product) continue;

        const costPrice = product.standard_price || 0;
        if (costPrice <= 0) continue;

        const salePrice = line.get_unit_price();
        if (salePrice < costPrice) {
            violations.push({
                productName: product.display_name,
                salePrice: salePrice,
                costPrice: costPrice,
            });
        }
    }
    return violations;
}

/**
 * Format violation list into a readable string.
 */
function formatViolations(violations, currency) {
    return violations
        .map(v =>
            `• ${v.productName}\n` +
            `  Sale Price: ${currency}${v.salePrice.toFixed(2)}  |  ` +
            `Cost Price: ${currency}${v.costPrice.toFixed(2)}`
        )
        .join("\n");
}

// ── Patch PaymentScreen to block payment if price below cost ──────────────────
patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
    },

    async validateOrder(isForceValidate) {
        const config = this.pos.config;
        // Check system parameter sent from backend via POS config
        const blockBelowCost = this.pos.session._server_data?.block_sale_below_cost ?? false;
        const allowManagerOverride = this.pos.session._server_data?.allow_manager_override ?? false;
        const isManager = this.pos.session._server_data?.current_user_is_manager ?? false;

        if (blockBelowCost) {
            if (!(allowManagerOverride && isManager)) {
                const currencySymbol =
                    this.pos.currency?.symbol || this.pos.currency?.name || "";
                const violations = getViolations(
                    this.currentOrder,
                    this.pos.db?.product_by_id || {}
                );

                if (violations.length > 0) {
                    const details = formatViolations(violations, currencySymbol);
                    this.dialog.add(ConfirmationDialog, {
                        title: _t("⚠️ Cannot Process Payment — Price Below Cost!"),
                        body:
                            _t(
                                "The following products are priced below their cost price:\n\n"
                            ) +
                            details +
                            "\n\n" +
                            _t(
                                "Please go back and adjust the prices before proceeding."
                            ),
                        confirmLabel: _t("Go Back"),
                        cancel: undefined, // no cancel button
                    });
                    return; // Block payment
                }
            }
        }

        return super.validateOrder(isForceValidate);
    },
});

// ── Patch ProductScreen to warn immediately when price is set below cost ──────
patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
    },

    async setPriceList(pricelist) {
        await super.setPriceList(...arguments);
        this._checkCurrentLineBelowCost();
    },

    _checkCurrentLineBelowCost() {
        const blockBelowCost =
            this.pos.session._server_data?.block_sale_below_cost ?? false;
        if (!blockBelowCost) return;

        const order = this.currentOrder;
        if (!order) return;

        const selectedLine = order.get_selected_orderline();
        if (!selectedLine) return;

        const product = selectedLine.product;
        if (!product) return;

        const costPrice = product.standard_price || 0;
        if (costPrice <= 0) return;

        const salePrice = selectedLine.get_unit_price();
        const currencySymbol =
            this.pos.currency?.symbol || this.pos.currency?.name || "";

        if (salePrice < costPrice) {
            // Show inline warning (non-blocking) so cashier is aware
            this.dialog.add(ConfirmationDialog, {
                title: _t("⚠️ Price Below Cost Warning"),
                body:
                    `${_t("Product")}: ${product.display_name}\n` +
                    `${_t("Sale Price")}: ${currencySymbol}${salePrice.toFixed(2)}\n` +
                    `${_t("Cost Price")}: ${currencySymbol}${costPrice.toFixed(2)}\n\n` +
                    _t(
                        "This price is below the product cost. " +
                        "Payment will be blocked unless the price is corrected."
                    ),
                confirmLabel: _t("OK"),
                cancel: undefined,
            });
        }
    },
});
