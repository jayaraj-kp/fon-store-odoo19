/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

const TARGET_MODELS = [
    "purchase.order",
    "purchase.order.line",
    "sale.order",
    "sale.order.line",
];

const TARGET_FIELDS = ["product_id", "product_template_id"];

patch(Many2XAutocomplete.prototype, {
    /**
     * getSources() builds the autocomplete option list, including
     * the "Create X" and "Create and edit..." entries.
     * We strip those entries when inside a product field on purchase/sale models.
     */
    async getSources(request) {
        const sources = await super.getSources(request);

        const fieldName = this.props.fieldString
            ? undefined
            : this.props.name;

        // Detect field name from props
        const name = this.props.name || "";
        // Detect model from closest record context
        const resModel =
            this.props.resModel ||
            this.env?.model?.config?.resModel ||
            "";

        const shouldHide =
            TARGET_FIELDS.includes(name) && TARGET_MODELS.includes(resModel);

        if (!shouldHide) {
            return sources;
        }

        // Filter out quick-create options from every source
        return sources.map((source) => {
            if (!source.options) return source;
            return {
                ...source,
                options: source.options.filter
                    ? source.options.filter(
                          (opt) =>
                              opt.action !== "quick_create" &&
                              opt.action !== "create_edit"
                      )
                    : source.options,
            };
        });
    },

    /**
     * Also override the computed options getter used in newer Odoo 19 builds
     * that call getOptions() instead of getSources().
     */
    get optionalCreateOptions() {
        const name = this.props.name || "";
        const resModel =
            this.props.resModel ||
            this.env?.model?.config?.resModel ||
            "";

        if (TARGET_FIELDS.includes(name) && TARGET_MODELS.includes(resModel)) {
            return [];
        }
        return super.optionalCreateOptions;
    },
});
