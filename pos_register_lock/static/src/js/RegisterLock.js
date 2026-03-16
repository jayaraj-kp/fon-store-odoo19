/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ClosePosPopup } from "@point_of_sale/app/navbar/close_pos_popup/close_pos_popup";
import { useService } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";

/**
 * Patch the ClosePosPopup (Closing Register popup) to add a
 * "Lock Register" button. When clicked:
 *  1. Calls pos.session.action_lock_register() via RPC
 *  2. Shows a locked overlay so the cashier cannot interact
 *  3. Polls every 5s until manager unlocks from backend
 */
patch(ClosePosPopup.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.lockState = useState({ locked: false, checking: false });
        this._pollInterval = null;
    },

    async lockRegister() {
        const sessionId = this.pos.session.id;
        try {
            await this.orm.call("pos.session", "action_lock_register", [[sessionId]]);
            this.lockState.locked = true;
            this._startPolling(sessionId);
        } catch (error) {
            this.notification.add(
                error.data?.message || "Failed to lock register.",
                { type: "danger" }
            );
        }
    },

    _startPolling(sessionId) {
        // Poll every 5 seconds to check if manager has unlocked
        this._pollInterval = setInterval(async () => {
            try {
                const result = await this.orm.read(
                    "pos.session",
                    [sessionId],
                    ["register_locked"]
                );
                if (result && result[0] && result[0].register_locked === false) {
                    this.lockState.locked = false;
                    clearInterval(this._pollInterval);
                    this._pollInterval = null;
                }
            } catch (_e) {
                // network error, keep polling
            }
        }, 5000);
    },

    __destroy() {
        if (this._pollInterval) {
            clearInterval(this._pollInterval);
        }
        super.__destroy?.(...arguments);
    },
});
