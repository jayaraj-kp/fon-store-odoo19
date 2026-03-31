/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";

/**
 * SqftButtonField
 *
 * A minimal field widget that renders as a focusable calculator icon button.
 * Because it is a *field* widget (not a plain <button>), Odoo's list renderer
 * includes it in the Tab-key cycle automatically.
 *
 * Behaviour:
 *   Tab  → focus moves onto this button
 *   Enter / Space  → opens the Sq.Ft Calculator wizard popup
 *   Click          → same as Enter
 */
class SqftButtonField extends Component {
    static template = "sale_sqft_calculator.SqftButtonField";

    // Accept all standard field widget props (name, record, readonly …)
    static props = {
        "*": true,
    };

    setup() {
        this.actionService = useService("action");
    }

    /** Only render the button when a product is already chosen on this line. */
    get hasProduct() {
        return !!(
            this.props.record &&
            this.props.record.data &&
            this.props.record.data.product_id &&
            this.props.record.data.product_id[0]
        );
    }

    /** Enter or Space while focused → open wizard */
    onKeyDown(ev) {
        if (ev.key === "Enter" || ev.key === " ") {
            ev.preventDefault();
            ev.stopPropagation();
            this._openWizard();
        }
    }

    /** Mouse click → open wizard */
    onClick(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this._openWizard();
    }

    async _openWizard() {
        if (!this.hasProduct) return;

        const record = this.props.record;

        // Make sure the line has been saved so the server knows its id
        if (record.isNew) {
            try {
                await record.save();
            } catch (_e) {
                return;
            }
        }

        await this.actionService.doActionButton({
            type: "object",
            name: "action_open_sqft_wizard",
            resModel: "sale.order.line",
            resId: record.resId,
            resIds: [record.resId],
            context: {},
        });
    }
}

// Register in the "fields" registry so the view can use widget="sqft_button_field"
registry.category("fields").add("sqft_button_field", {
    component: SqftButtonField,
    displayName: "Sqft Calculator Button",
    supportedTypes: ["boolean"],
    isEmpty: () => false,
});
