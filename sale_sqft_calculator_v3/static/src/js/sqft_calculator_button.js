/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * SqftCalculatorButton — OWL field widget
 *
 * Renders a 📐 calculator icon button after the product field in sale order lines.
 * - Tab key moves focus to this button
 * - Enter key opens the Square Feet Calculator popup
 */
export class SqftCalculatorButton extends Component {
    static template = "sale_sqft_calculator.SqftCalculatorButton";
    static props = {
        record: { type: Object },
        readonly: { type: Boolean, optional: true },
        // standard field widget props
        name: { type: String, optional: true },
        id: { type: String, optional: true },
        "*": true,
    };

    setup() {
        this.action = useService("action");
    }

    /**
     * Show button only when a product is selected on the line.
     */
    get isVisible() {
        return !!this.props.record.data.product_id;
    }

    /**
     * Enter key → open wizard  |  Space key → open wizard
     */
    onKeyDown(ev) {
        if (ev.key === "Enter" || ev.key === " ") {
            ev.preventDefault();
            ev.stopPropagation();
            this.openWizard();
        }
    }

    /**
     * Click or keyboard → call the server action that opens the wizard popup.
     */
    async openWizard() {
        if (!this.isVisible) return;
        const record = this.props.record;

        // Save the line first so the wizard can load the record
        if (record.isNew) {
            await record.save();
        }

        await this.action.doActionButton({
            type: "object",
            name: "action_open_sqft_wizard",
            resModel: "sale.order.line",
            resId: record.resId,
            resIds: [record.resId],
            context: record.context || {},
        });
    }
}

registry.category("fields").add("sqft_calculator_button", {
    component: SqftCalculatorButton,
    displayName: "Sqft Calculator Button",
    supportedTypes: ["boolean"],
});
