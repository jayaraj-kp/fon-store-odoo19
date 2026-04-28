/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";

/**
 * Patch Many2OneField to disable "Create" and "Create and edit..."
 * quick-create options when the field is `product_id` inside
 * purchase.order or sale.order models.
 */
patch(Many2OneField.prototype, {
    setup() {
        super.setup(...arguments);
    },

    get canQuickCreate() {
        if (this._shouldHideQuickCreate()) {
            return false;
        }
        return super.canQuickCreate;
    },

    get canCreateEdit() {
        if (this._shouldHideQuickCreate()) {
            return false;
        }
        return super.canCreateEdit;
    },

    _shouldHideQuickCreate() {
        const fieldName = this.props.name;
        const model = this.props.record?.model?.config?.resModel
            || this.props.record?.resModel
            || "";

        const targetModels = [
            "purchase.order",
            "purchase.order.line",
            "sale.order",
            "sale.order.line",
        ];
        const targetFields = ["product_id", "product_template_id"];

        return targetFields.includes(fieldName) && targetModels.includes(model);
    },
});
