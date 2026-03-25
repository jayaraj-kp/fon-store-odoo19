/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { useState, onMounted } from "@odoo/owl";

/**
 * Helper: call a JSON-RPC route directly via fetch.
 * This bypasses the ORM access-rights check that blocks POS employee users.
 */
async function jsonRpc(route, params = {}) {
    const response = await fetch(route, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            jsonrpc: "2.0",
            method: "call",
            id: Math.floor(Math.random() * 1000000),
            params: params,
        }),
    });
    const data = await response.json();
    if (data.error) {
        throw new Error(data.error.data?.message || data.error.message || "RPC Error");
    }
    return data.result;
}

patch(Navbar.prototype, {
    setup() {
        super.setup(...arguments);
        this.notification = useService("notification");
        this.cashTransferState = useState({ sessions: [] });

        onMounted(async () => {
            await this._loadOpenSessions();
        });
    },

    async _loadOpenSessions() {
        try {
            const sessionId = this.pos?.session?.id;
            if (!sessionId) return;

            const sessions = await jsonRpc(
                "/pos/cash_transfer/get_sessions",
                { current_session_id: sessionId }
            );
            this.cashTransferState.sessions = sessions || [];
        } catch (e) {
            console.error("[CashTransfer] Failed to load sessions:", e);
        }
    },

    async openCashTransferDialog() {
        const sessionId = this.pos?.session?.id;
        if (!sessionId) {
            this.notification.add("Session not found!", { type: "danger" });
            return;
        }

        // Refresh open sessions every time dialog opens
        await this._loadOpenSessions();

        if (!this.cashTransferState.sessions.length) {
            this.notification.add(
                "No other open POS counters found! Please open another counter first.",
                { type: "warning", sticky: false }
            );
            return;
        }

        // Step 1: Select destination counter
        const sessionOptions = this.cashTransferState.sessions
            .map((s, i) => `${i + 1}. ${s.pos_name} (Cashier: ${s.cashier})`)
            .join("\n");

        const choiceStr = prompt(
            `💸 Cash Transfer\n\nSelect destination counter:\n${sessionOptions}\n\nEnter number (1–${this.cashTransferState.sessions.length}):`
        );
        if (!choiceStr) return;

        const choiceIdx = parseInt(choiceStr, 10) - 1;
        if (isNaN(choiceIdx) || choiceIdx < 0 ||
            choiceIdx >= this.cashTransferState.sessions.length) {
            alert("Invalid selection! Please enter a valid number.");
            return;
        }

        const toSession = this.cashTransferState.sessions[choiceIdx];

        // Step 2: Enter amount
        const amountStr = prompt(
            `Transfer to: ${toSession.pos_name}\n\nEnter amount (Rs.):`
        );
        if (!amountStr) return;

        const amount = parseFloat(amountStr);
        if (isNaN(amount) || amount <= 0) {
            alert("Please enter a valid amount greater than 0!");
            return;
        }

        // Step 3: Optional reason
        const reason = prompt("Reason (optional):") || "";

        // Step 4: Confirm
        const confirmed = confirm(
            `Confirm Transfer\n\nFrom: Current Counter\nTo: ${toSession.pos_name}\nAmount: Rs. ${amount.toFixed(2)}${reason ? "\nReason: " + reason : ""}\n\nProceed?`
        );
        if (!confirmed) return;

        // Step 5: Execute transfer via HTTP route
        try {
            const result = await jsonRpc(
                "/pos/cash_transfer/process",
                {
                    from_session_id: sessionId,
                    to_session_id: toSession.id,
                    amount: amount,
                    reason: reason,
                }
            );

            if (result && result.success) {
                this.notification.add(
                    `✅ Rs. ${amount.toFixed(2)} transferred to ${toSession.pos_name}! (Ref: ${result.transfer_name})`,
                    { type: "success", sticky: false }
                );
            } else {
                this.notification.add(
                    `❌ Transfer failed: ${result ? result.error : "Unknown error"}`,
                    { type: "danger", sticky: false }
                );
            }
        } catch (e) {
            console.error("[CashTransfer] Transfer error:", e);
            this.notification.add(
                "Transfer error: " + (e.message || String(e)),
                { type: "danger", sticky: false }
            );
        }
    },
});
