/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { useState, onMounted } from "@odoo/owl";

patch(Navbar.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.cashTransferState = useState({ sessions: [] });

        onMounted(async () => {
            try {
                const sessionId = this.pos?.session?.id;
                if (!sessionId) return;
                const sessions = await this.orm.call(
                    "pos.session",
                    "get_open_sessions_for_transfer",
                    [sessionId]
                );
                this.cashTransferState.sessions = sessions || [];
            } catch (e) {
                console.error("[CashTransfer] Failed to load sessions:", e);
            }
        });
    },

    async openCashTransferDialog() {
        const sessionId = this.pos?.session?.id;
        if (!sessionId) return;

        // Refresh open sessions
        try {
            const sessions = await this.orm.call(
                "pos.session",
                "get_open_sessions_for_transfer",
                [sessionId]
            );
            this.cashTransferState.sessions = sessions || [];
        } catch (e) {
            this.env.services.notification.add(
                "Could not load open sessions!",
                { type: "danger" }
            );
            return;
        }

        if (!this.cashTransferState.sessions.length) {
            this.env.services.notification.add(
                "No other open POS counters found! Please open another counter first.",
                { type: "warning", sticky: false }
            );
            return;
        }

        // Build simple prompt
        const sessionOptions = this.cashTransferState.sessions
            .map((s, i) => `${i + 1}. ${s.pos_name}`)
            .join("\n");

        const choiceStr = prompt(
            `Cash Transfer\n\nSelect destination counter:\n${sessionOptions}\n\nEnter number (1-${this.cashTransferState.sessions.length}):`
        );
        if (!choiceStr) return;

        const choiceIdx = parseInt(choiceStr) - 1;
        if (isNaN(choiceIdx) || choiceIdx < 0 ||
            choiceIdx >= this.cashTransferState.sessions.length) {
            alert("Invalid selection!");
            return;
        }

        const toSession = this.cashTransferState.sessions[choiceIdx];

        const amountStr = prompt(
            `Transfer to: ${toSession.pos_name}\n\nEnter amount (Rs.):`
        );
        if (!amountStr) return;

        const amount = parseFloat(amountStr);
        if (isNaN(amount) || amount <= 0) {
            alert("Please enter a valid amount!");
            return;
        }

        const reason = prompt("Reason (optional):") || "";

        try {
            const result = await this.orm.call(
                "pos.cash.transfer",
                "create_transfer_from_pos",
                [],
                {
                    from_session_id: sessionId,
                    to_session_id: toSession.id,
                    amount: amount,
                    reason: reason,
                }
            );

            if (result.success) {
                this.env.services.notification.add(
                    `✅ Rs. ${amount.toFixed(2)} transferred to ${toSession.pos_name}! (${result.transfer_name})`,
                    { type: "success", sticky: false }
                );
            } else {
                this.env.services.notification.add(
                    `❌ Transfer failed: ${result.error}`,
                    { type: "danger", sticky: false }
                );
            }
        } catch (e) {
            this.env.services.notification.add(
                "Transfer error: " + (e.message || e),
                { type: "danger", sticky: false }
            );
        }
    },
});
