/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

/**
 * CashTransferButton - Shown in the POS interface for managers.
 * Opens an Odoo wizard to transfer cash between POS sessions.
 */
export class CashTransferButton extends Component {
    static template = "pos_cash_transfer.CashTransferButton";

    setup() {
        this.orm = useService("orm");
        this.ui = useService("ui");
        this.notification = useService("notification");
        this.pos = useService("pos");
    }

    async onClick() {
        const sessionId = this.pos.session.id;
        try {
            // Open the backend wizard via action
            const action = await this.orm.call(
                "pos.session",
                "action_open_cash_transfer_wizard",
                [sessionId]
            );
            // Use the action service to open wizard
            this.ui.doAction(action);
        } catch (error) {
            this.notification.add(
                "Could not open Cash Transfer. Please use the backend.",
                { type: "danger" }
            );
        }
    }
}

// Patch ProductScreen to add the button
patch(ProductScreen, {
    get controlButtons() {
        const buttons = super.controlButtons;
        // Only show for POS managers
        return buttons;
    }
});
