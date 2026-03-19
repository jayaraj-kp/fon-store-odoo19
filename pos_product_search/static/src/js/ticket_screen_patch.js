/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { _t } from "@web/core/l10n/translation";

/**
 * Patch the TicketScreen to add a "Product" search filter.
 *
 * How it works:
 * 1. `searchFields` getter — adds the "Product" entry so it appears
 *    in the autocomplete dropdown alongside Reference, Receipt Number, etc.
 * 2. `_searchOrder` — handles the actual filtering logic for the new field
 *    by inspecting every order line's product name.
 */
patch(TicketScreen.prototype, {

    // -------------------------------------------------------------------------
    // Extend the search-fields map
    // -------------------------------------------------------------------------
    get searchFields() {
        const fields = super.searchFields;
        return {
            ...fields,
            PRODUCT: {
                displayName: _t("Product"),
                // "lines" is the modelField key; filtering is handled manually
                // in _searchOrder because it requires iterating order lines.
                modelField: "lines",
            },
        };
    },

    // -------------------------------------------------------------------------
    // Extend the per-order search predicate
    // -------------------------------------------------------------------------
    /**
     * @param {import("@point_of_sale/app/store/pos_order").PosOrder} order
     * @param {{ fieldName: string, searchTerm: string }} searchDetails
     * @returns {boolean}
     */
    _searchOrder(order, searchDetails) {
        if (searchDetails.fieldName === "PRODUCT") {
            const term = (searchDetails.searchTerm || "").trim().toLowerCase();
            if (!term) {
                return true; // empty search → show all
            }

            // order.lines is the array of PosOrderline objects
            const lines = order.lines || [];
            return lines.some((line) => {
                // Try every possible property name used across Odoo versions
                const productName = (
                    line.product?.display_name ||
                    line.product?.name ||
                    line.full_product_name ||
                    line.product_name ||
                    ""
                ).toLowerCase();
                return productName.includes(term);
            });
        }

        // Delegate all other field searches to the original implementation
        return super._searchOrder(order, searchDetails);
    },
});
