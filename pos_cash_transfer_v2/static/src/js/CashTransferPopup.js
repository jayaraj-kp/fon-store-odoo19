/** @odoo-module **/

import { Component, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/store/pos_hook";

export class CashTransferPopup extends Component {
    static template = "pos_cash_transfer.CashTransferPopup";
    static props = {
        close: Function,
    };

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            sessions: [],
            selectedId: 0,
            amount: "",
            reason: "",
            loading: true,
            error: "",
            processing: false,
        });

        onMounted(async () => {
            try {
                const sessions = await this.orm.call(
                    "pos.session",
                    "get_open_sessions_for_transfer",
                    [this.pos.session.id]
                );
                this.state.sessions = sessions;
                if (sessions.length > 0) {
                    this.state.selectedId = sessions[0].id;
                }
            } catch (e) {
                this.state.error = "Could not load open sessions.";
            } finally {
                this.state.loading = false;
            }
        });
    }

    onSessionChange(ev) {
        this.state.selectedId = parseInt(ev.target.value);
        this.state.error = "";
    }

    onAmountChange(ev) {
        this.state.amount = ev.target.value;
        this.state.error = "";
    }

    onReasonChange(ev) {
        this.state.reason = ev.target.value;
    }

    get selectedSession() {
        return this.state.sessions.find(s => s.id === this.state.selectedId);
    }

    async onTransfer() {
        if (!this.state.selectedId) {
            this.state.error = "Please select a destination counter!";
            return;
        }
        const amount = parseFloat(this.state.amount);
        if (!amount || amount <= 0) {
            this.state.error = "Please enter a valid amount greater than 0!";
            return;
        }

        this.state.processing = true;
        this.state.error = "";

        try {
            const result = await this.orm.call(
                "pos.cash.transfer",
                "create_transfer_from_pos",
                [],
                {
                    from_session_id: this.pos.session.id,
                    to_session_id: this.state.selectedId,
                    amount: amount,
                    reason: this.state.reason,
                }
            );

            if (result.success) {
                this.notification.add(result.message, {
                    type: "success",
                    title: "✅ Transfer Successful!",
                });
                this.props.close();
            } else {
                this.state.error = result.error || "Transfer failed!";
            }
        } catch (e) {
            this.state.error = "An error occurred. Please try again.";
        } finally {
            this.state.processing = false;
        }
    }

    onCancel() {
        this.props.close();
    }
}
