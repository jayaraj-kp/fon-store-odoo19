/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

/**
 * ROOT CAUSE (Odoo 19):
 * Many2XAutocomplete no longer uses getSources() to add Create/Create&Edit.
 * Instead it calls addCreateSuggestion() and addCreateEditSuggestion()
 * as separate methods during option building.
 *
 * We patch those two methods to be no-ops when the field is a product field,
 * detected via:
 *   - this.props.id  (e.g. "product_id_0", "product_template_id_0")
 *   - this.props.resModel (e.g. "product.product", "product.template")
 */

const TARGET_FIELD_PREFIXES = ["product_id", "product_template_id"];
const TARGET_RES_MODELS = ["product.product", "product.template"];

function isProductField(component) {
    const id = component.props?.id || "";
    const resModel = component.props?.resModel || "";

    const fieldMatch = TARGET_FIELD_PREFIXES.some(
        (prefix) => id === prefix || id.startsWith(prefix + "_")
    );
    const modelMatch = TARGET_RES_MODELS.includes(resModel);

    // Match either: field name OR resModel (belt-and-suspenders)
    return fieldMatch || modelMatch;
}

patch(Many2XAutocomplete.prototype, {
    /**
     * Suppress "Create X" quick-create suggestion on product fields.
     */
    addCreateSuggestion(suggestions, request) {
        if (isProductField(this)) return;
        return super.addCreateSuggestion(suggestions, request);
    },

    /**
     * Suppress "Create and edit..." suggestion on product fields.
     */
    addCreateEditSuggestion(suggestions, request) {
        if (isProductField(this)) return;
        return super.addCreateEditSuggestion(suggestions, request);
    },
});