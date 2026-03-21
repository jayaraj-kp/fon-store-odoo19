/** @odoo-module **/

/**
 * POS Product Search Filter — v5 (Odoo 17/18/19 CE)
 *
 * KEY INSIGHT: In Odoo 17+, TicketScreen's XML template already loops over
 * getSearchFields() results automatically using t-foreach. This means the
 * XML patch is NOT needed — and was actually causing the crash by trying
 * to XPath-match a <ul class="py-1"> that no longer exists in Odoo 19.
 *
 * All we need is this JS patch that:
 * 1. Adds PRODUCT to getSearchFields() → appears in the dropdown automatically
 * 2. Handles filtering in _doesOrderPassFilter() → Odoo 19 method
 *    (with fallbacks for 17/18 method names)
 */

import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { _t } from "@web/core/l10n/translation";

/**
 * Collect all product names from an order's lines as a lowercase string.
 * Tries every known field path across Odoo versions.
 */
function getOrderProductNames(order) {
    const lines =
        (typeof order.get_orderlines === "function" && order.get_orderlines()) ||
        order.lines ||
        order.orderlines ||
        [];

    return Array.from(lines)
        .map((line) => {
            return (
                (typeof line.get_full_product_name === "function" && line.get_full_product_name()) ||
                line.full_product_name ||
                line.product_name ||
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
     * Odoo 17/18/19 — called to populate the search-field dropdown.
     * The template iterates over Object.entries(getSearchFields()) automatically,
     * so returning PRODUCT here is all that is needed for the UI.
     */
    getSearchFields() {
        let fields = {};
        try {
            fields = super.getSearchFields() || {};
        } catch (_e) {
            // super may not define it in some builds
        }
        return {
            ...fields,
            PRODUCT: {
                displayName: _t("Product"),
                modelField: "lines.product_id.display_name",
                repr: (order) => getOrderProductNames(order),
            },
        };
    },

    /**
     * Odoo 19 primary filter method — called per order when searching.
     */
    _doesOrderPassFilter(order, { fieldName, searchTerm }) {
        if (fieldName === "PRODUCT") {
            const term = (searchTerm || "").toLowerCase().trim();
            if (!term) return true;
            return getOrderProductNames(order).includes(term);
        }
        try {
            return super._doesOrderPassFilter(order, { fieldName, searchTerm });
        } catch (_e) {
            return true;
        }
    },

    /**
     * Odoo 17/18 fallback filter method name.
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
     * Odoo 16/17 fallback filter method name.
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