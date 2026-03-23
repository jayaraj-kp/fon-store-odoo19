/** @odoo-module **/

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { CashTransferPopup } from "./CashTransferPopup";

export class CashTransferButton extends Component {
    static template = "pos_cash_transfer.CashTransferButton";
    static props = {};

    setup() {
        this.pos = usePos();
        this.popup = useService("popup");
    }

    async onClick() {
        const { confirmed, payload } = await this.popup.add(CashTransferPopup, {
            title: "Cash Transfer Between Counters",
            currentSessionId: this.pos.session.id,
        });

        if (confirmed && payload) {
            await this._processCashTransfer(payload);
        }
    }

    async _processCashTransfer(payload) {
        try {
            const result = await this.pos.env.services.orm.call(
                "pos.cash.transfer",
                "create_transfer_from_pos",
                [],
                {
                    from_session_id: this.pos.session.id,
                    to_session_id: payload.toSessionId,
                    amount: payload.amount,
                    reason: payload.reason,
                }
            );

            if (result.success) {
                this.pos.env.services.notification.add(
                    result.message,
                    { type: "success", title: "Transfer Successful!" }
                );
            } else {
                this.pos.env.services.notification.add(
                    result.error,
                    { type: "danger", title: "Transfer Failed!" }
                );
            }
        } catch (error) {
            this.pos.env.services.notification.add(
                "An error occurred during cash transfer!",
                { type: "danger", title: "Error" }
            );
        }
    }
}
