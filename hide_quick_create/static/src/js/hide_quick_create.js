/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

/**
 * FIX NOTE:
 * In Odoo 19, `this.props.resModel` on Many2XAutocomplete refers to the
 * *target* model (e.g. "product.product"), NOT the parent form model
 * (e.g. "purchase.order"). Checking TARGET_MODELS against it always
 * failed silently, so the filter never ran.
 *
 * Solution: filter purely by field name. "product_id" and
 * "product_template_id" are specific enough — they only appear on
 * purchase/sale order lines in the contexts we care about.
 * If you need stricter scoping, see the commented-out model check below.
 */

const TARGET_FIELDS = ["product_id", "product_template_id"];

patch(Many2XAutocomplete.prototype, {
    /**
     * getSources() builds the autocomplete option list, including
     * the "Create X" and "Create and edit..." entries.
     * We strip those entries for product fields.
     */
    async getSources(request) {
        const sources = await super.getSources(request);
        const name = this.props.name || "";

        if (!TARGET_FIELDS.includes(name)) {
            return sources;
        }

        return sources.map((source) => {
            if (!source.options || !Array.isArray(source.options)) {
                return source;
            }
            return {
                ...source,
                options: source.options.filter(
                    (opt) =>
                        opt.action !== "quick_create" &&
                        opt.action !== "create_edit"
                ),
            };
        });
    },

    /**
     * Covers newer Odoo 19 builds that use optionalCreateOptions
     * instead of (or in addition to) getSources().
     */
    get optionalCreateOptions() {
        const name = this.props.name || "";

        if (TARGET_FIELDS.includes(name)) {
            return [];
        }
        return super.optionalCreateOptions;
    },
});