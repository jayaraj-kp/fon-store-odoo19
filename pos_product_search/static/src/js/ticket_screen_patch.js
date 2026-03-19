/** @odoo-module **/

/**
 * POS Product Search Filter — Odoo 17 / 18 / 19 CE
 *
 * Root cause of v1 failure:
 *   - Used `get searchFields()` getter + `_searchOrder()` — those names do NOT
 *     exist in Odoo 17+ OWL rewrite.
 *   - Odoo 17/18/19 uses `getSearchFields()` (a plain method, no underscore).
 *     The base implementation calls `repr(order)` on the returned field
 *     descriptor and checks whether the result string contains the search term.
 *
 * Fix:
 *   - Patch `getSearchFields()` with the correct name.
 *   - Provide a `repr` function that collects every product name on the order's
 *     lines and joins them into a single searchable string.
 *   - No need to patch `_searchOrder` — the base class already uses `repr`.
 */

import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { _t } from "@web/core/l10n/translation";

patch(TicketScreen.prototype, {

    /**
     * Override getSearchFields() — the correct Odoo 17/18/19 method name.
     *
     * Each field descriptor must have:
     *   repr(order)  → string that will be searched
     *   displayName  → label shown in the autocomplete dropdown
     *   modelField   → backend field (used for server-side filtering; we set a
     *                  reasonable value even though our filter is client-side)
     */
    getSearchFields() {
        // Call super to keep all default fields (Reference, Receipt Number, etc.)
        const fields = super.getSearchFields(...arguments);

        return {
            ...fields,
            PRODUCT: {
                displayName: _t("Product"),
                modelField: "lines.product_id.display_name",

                /**
                 * repr is called for each order in the list.
                 * We concatenate all product names from every line so that
                 * typing any part of a product name will match the order.
                 */
                repr: (order) => {
                    const lines = order.lines || [];
                    return lines
                        .map((line) =>
                            // Try all possible property paths used across versions
                            line.product_name ||          // serialised sync field
                            line.full_product_name ||     // older OWL model
                            (line.product && (
                                line.product.display_name ||
                                line.product.name
                            )) ||
                            ""
                        )
                        .filter(Boolean)
                        .join(" | ");   // e.g. "LAP TOP | MULTI CHARGER | mouse"
                },
            },
        };
    },
});
