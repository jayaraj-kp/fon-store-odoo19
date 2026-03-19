/** @odoo-module **/

/**
 * POS Product Search Filter — v3 (Odoo 19 CE)
 *
 * Strategy:
 *  1. The XML template patch adds the "Product" <li> to the dropdown UI.
 *  2. This JS patch hooks into the filtering logic so selecting "Product"
 *     actually filters orders by product name.
 *
 * Debug logging is included so you can check the browser console (F12)
 * and see exactly which methods are found on the prototype.
 */

import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { _t } from "@web/core/l10n/translation";

// ── Debug: log ALL methods on TicketScreen.prototype ──────────────────────
console.group("[POS Product Search] TicketScreen prototype methods");
const protoMethods = [];
let obj = TicketScreen.prototype;
while (obj && obj !== Object.prototype) {
    Object.getOwnPropertyNames(obj).forEach((name) => {
        if (typeof TicketScreen.prototype[name] === "function") {
            protoMethods.push(name);
        }
    });
    obj = Object.getPrototypeOf(obj);
}
// Log all method names sorted so you can find the real search-related ones
console.log("All methods:", protoMethods.sort().join(", "));
// Specifically look for search-related methods
const searchMethods = protoMethods.filter((m) =>
    m.toLowerCase().includes("search") || m.toLowerCase().includes("filter")
);
console.log("Search / filter methods found:", searchMethods);
console.groupEnd();
// ─────────────────────────────────────────────────────────────────────────

/**
 * Helper: get all product names from an order's lines as a
 * lowercase space-separated string for substring matching.
 */
function getOrderProductNames(order) {
    const lines = order.lines || [];
    return lines
        .map(
            (line) =>
                line.product_name ||
                line.full_product_name ||
                (line.product && (line.product.display_name || line.product.name)) ||
                ""
        )
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
}

// ── Patch 1: getSearchFields (Odoo 17/18/19 name) ──────────────────────
patch(TicketScreen.prototype, {
    getSearchFields() {
        console.log("[POS Product Search] getSearchFields() called ✓");
        let fields = {};
        try {
            fields = super.getSearchFields(...arguments) || {};
        } catch (e) {
            console.warn("[POS Product Search] super.getSearchFields failed:", e);
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

    // ── Patch 2: _searchOrder — called for each order to decide visibility
    // Method name used in Odoo 16/17/18; we patch it here too as a safety net.
    _searchOrder(order, fieldValue) {
        if (fieldValue && fieldValue.fieldName === "PRODUCT") {
            const term = (fieldValue.searchTerm || "").toLowerCase().trim();
            if (!term) return true;
            return getOrderProductNames(order).includes(term);
        }
        try {
            return super._searchOrder(order, fieldValue);
        } catch (e) {
            return true;
        }
    },

    // ── Patch 3: filterOrders / applyFilters — some versions use this name
    filterOrderBySearch(order, searchDetails) {
        if (searchDetails && searchDetails.fieldName === "PRODUCT") {
            const term = (searchDetails.searchTerm || "").toLowerCase().trim();
            if (!term) return true;
            return getOrderProductNames(order).includes(term);
        }
        try {
            return super.filterOrderBySearch(order, searchDetails);
        } catch (e) {
            return true;
        }
    },
});

console.log("[POS Product Search] Patch applied successfully ✓");
