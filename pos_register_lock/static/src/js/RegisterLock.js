/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { useState, onWillDestroy, onMounted } from "@odoo/owl";
import { Chrome } from "@point_of_sale/app/pos_app";

/**
 * Patch POS Chrome to:
 * 1. Detect initial lock state
 * 2. Show full-screen overlay when locked
 * 3. Poll every 5s for unlock
 * 4. Expose lockRegister() so the Lock button (injected via DOM) can call it
 */
patch(Chrome.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.registerLockState = useState({ locked: false });
        this._lockPollInterval = null;

        onMounted(() => {
            // Check if session is already locked on load
            const session = this.pos?.session;
            if (session?.register_locked) {
                this.registerLockState.locked = true;
                this._startLockPolling();
            }
            // Expose lockRegister on window so XML button can call it
            window.__posRegisterLock = () => this.lockRegister();
        });

        onWillDestroy(() => {
            if (this._lockPollInterval) clearInterval(this._lockPollInterval);
            delete window.__posRegisterLock;
        });
    },

    async lockRegister() {
        const sessionId = this.pos.session.id;
        try {
            await this.orm.call("pos.session", "action_lock_register", [[sessionId]]);
            this.registerLockState.locked = true;
            this._startLockPolling();
        } catch (e) {
            console.error("[RegisterLock] Lock failed:", e);
        }
    },

    _startLockPolling() {
        if (this._lockPollInterval) clearInterval(this._lockPollInterval);
        this._lockPollInterval = setInterval(async () => {
            try {
                const sessionId = this.pos.session.id;
                const result = await this.orm.read(
                    "pos.session", [sessionId], ["register_locked"]
                );
                if (result?.[0]?.register_locked === false) {
                    this.registerLockState.locked = false;
                    clearInterval(this._lockPollInterval);
                    this._lockPollInterval = null;
                }
            } catch (_) {}
        }, 5000);
    },
});
