/** @odoo-module **/

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class CashTransferPopup extends AbstractAwaitablePopup {
    static template = "pos_cash_transfer.CashTransferPopup";
    static defaultProps = {
        confirmText: "Transfer",
        cancelText: "Cancel",
        title: "Cash Transfer",
    };

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            openSessions: [],
            selectedSessionId: null,
            amount: "",
            reason: "",
            loading: true,
            error: "",
        });

        onMounted(async () => {
            await this._loadOpenSessions();
        });
    }

    async _loadOpenSessions() {
        try {
            this.state.loading = true;
            const sessions = await this.orm.call(
                "pos.session",
                "get_open_sessions_for_transfer",
                [this.props.currentSessionId],
                {}
            );
            this.state.openSessions = sessions;
            if (sessions.length > 0) {
                this.state.selectedSessionId = sessions[0].id;
            }
        } catch (e) {
            this.state.error = "Failed to load open sessions!";
        } finally {
            this.state.loading = false;
        }
    }

    onSessionChange(ev) {
        this.state.selectedSessionId = parseInt(ev.target.value);
    }

    onAmountChange(ev) {
        this.state.amount = ev.target.value;
        this.state.error = "";
    }

    onReasonChange(ev) {
        this.state.reason = ev.target.value;
    }

    _validate() {
        if (!this.state.selectedSessionId) {
            this.state.error = "Please select a destination counter!";
            return false;
        }
        const amount = parseFloat(this.state.amount);
        if (!amount || amount <= 0) {
            this.state.error = "Please enter a valid amount!";
            return false;
        }
        return true;
    }

    async confirm() {
        if (!this._validate()) return;

        const amount = parseFloat(this.state.amount);

        try {
            const result = await fetch("/pos/cash_transfer/create", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    jsonrpc: "2.0",
                    method: "call",
                    params: {
                        from_session_id: this.props.currentSessionId,
                        to_session_id: this.state.selectedSessionId,
                        amount: amount,
                        reason: this.state.reason,
                    },
                }),
            });

            const data = await result.json();
            const response = data.result;

            if (response && response.success) {
                super.confirm({
                    toSessionId: this.state.selectedSessionId,
                    amount: amount,
                    reason: this.state.reason,
                    transferName: response.transfer_name,
                    message: response.message,
                });
            } else {
                this.state.error = (response && response.error) ||
                    "Transfer failed!";
            }
        } catch (e) {
            this.state.error = "Network error. Please try again!";
        }
    }

    getSelectedSessionName() {
        const session = this.state.openSessions.find(
            (s) => s.id === this.state.selectedSessionId
        );
        return session ? session.pos_name : "";
    }
}
