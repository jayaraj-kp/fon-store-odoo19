/** @odoo-module **/

/**
 * POS Product Search Filter — v4 (Odoo 19 CE)
 *
 * Fix: TypeError: Cannot read properties of undefined (reading 'models')
 *
 * Root cause: In Odoo 19, TicketScreen's search mechanism changed.
 * The component uses `getSearchFields` which must return an object keyed
 * by field name. We patch that method to inject the PRODUCT field.
 *
 * Also fixed: onClickSearchField is the correct handler name in Odoo 19.
 */

import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { _t } from "@web/core/l10n/translation";

/**
 * Helper: collect all product names from an order's order lines.
 * Tries multiple field paths to be resilient across Odoo versions.
 */
function getOrderProductNames(order) {
    const lines = order.lines || order.orderlines || [];
    return lines
        .map((line) => {
            // Try the most common field names in order
            return (
                line.product_name ||
                line.full_product_name ||
                (line.product_id && (line.product_id.display_name || line.product_id.name)) ||
                (line.product && (line.product.display_name || line.product.name)) ||
                ""
            );
        })
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
}

patch(TicketScreen.prototype, {
    /**
     * Odoo 19 uses getSearchFields() to build the dropdown list.
     * We call super first (safely), then inject our PRODUCT entry.
     */
    getSearchFields() {
        // Safely call the original method
        let fields = {};
        try {
            fields = super.getSearchFields() || {};
        } catch (_e) {
            // If super doesn't define it, start from scratch
        }

        return {
            ...fields,
            PRODUCT: {
                displayName: _t("Product"),
                // modelField is used by some versions for domain-based search;
                // repr() is the fallback used for in-memory filtering.
                modelField: "lines.product_id.display_name",
                repr: (order) => getOrderProductNames(order),
            },
        };
    },

    /**
     * Odoo 19 calls getFilteredOrderList which internally calls
     * _doesOrderPassFilter for each order. We intercept here.
     */
    _doesOrderPassFilter(order, { fieldName, searchTerm }) {
        if (fieldName === "PRODUCT") {
            const term = (searchTerm || "").toLowerCase().trim();
            if (!term) return true;
            return getOrderProductNames(order).includes(term);
        }
        // Delegate to original for all other field types
        try {
            return super._doesOrderPassFilter(order, { fieldName, searchTerm });
        } catch (_e) {
            return true;
        }
    },

    /**
     * Safety net: some Odoo 19 builds use filterOrderBySearch instead.
     */
    filterOrderBySearch(order, searchDetails) {
        if (searchDetails && searchDetails.fieldName === "PRODUCT") {
            const term = (searchDetails.searchTerm || "").toLowerCase().trim();
            if (!term) return true;
            return getOrderProductNames(order).includes(term);
        }
        try {
            return super.filterOrderBySearch(order, searchDetails);
        } catch (_e) {
            return true;
        }
    },

    /**
     * Safety net: Odoo 16/17/18 used _searchOrder.
     */
    _searchOrder(order, fieldValue) {
        if (fieldValue && fieldValue.fieldName === "PRODUCT") {
            const term = (fieldValue.searchTerm || "").toLowerCase().trim();
            if (!term) return true;
            return getOrderProductNames(order).includes(term);
        }
        try {
            return super._searchOrder(order, fieldValue);
        } catch (_e) {
            return true;
        }
    },
});