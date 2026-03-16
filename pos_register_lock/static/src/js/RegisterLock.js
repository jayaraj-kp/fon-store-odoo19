/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { useState, onWillDestroy, onMounted } from "@odoo/owl";
import { Chrome } from "@point_of_sale/app/pos_app";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";

// Shared reactive lock state accessible by both Chrome and Navbar patches
const sharedLockState = { locked: false };

/**
 * Patch Chrome:
 * - Reads register_locked from session on every load (survives refresh)
 * - Shows full-screen overlay when locked
 * - Polls every 5s for manager unlock
 */
patch(Chrome.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.registerLockState = useState(sharedLockState);
        this._lockPollInterval = null;

        onMounted(() => {
            // Check lock state from backend session data (persists after refresh)
            const sessionId = this.pos?.session?.id;
            if (sessionId) {
                this.orm.read("pos.session", [sessionId], ["register_locked"]).then((result) => {
                    if (result?.[0]?.register_locked) {
                        this.registerLockState.locked = true;
                        this._startLockPolling(sessionId);
                    }
                }).catch(() => {});
            }
        });

        onWillDestroy(() => {
            if (this._lockPollInterval) clearInterval(this._lockPollInterval);
        });
    },

    _startLockPolling(sessionId) {
        if (this._lockPollInterval) clearInterval(this._lockPollInterval);
        this._lockPollInterval = setInterval(async () => {
            try {
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

/**
 * Patch Navbar:
 * - Adds lockRegister() method called from burger menu
 * - Blocks closeSession() when register is locked
 */
patch(Navbar.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.registerLockState = useState(sharedLockState);
    },

    async lockRegister() {
        try {
            await this.orm.call(
                "pos.session", "action_lock_register", [[this.pos.session.id]]
            );
            this.registerLockState.locked = true;
            // Kick off polling on Chrome instance
            document.dispatchEvent(new CustomEvent("pos-register-locked", {
                detail: { sessionId: this.pos.session.id }
            }));
        } catch (e) {
            console.error("[RegisterLock] Lock failed:", e);
        }
    },

    // Override closeSession to block when locked
    closeSession() {
        if (this.registerLockState.locked) {
            alert("❌ Register is locked. Ask your manager to unlock it first.");
            return;
        }
        return super.closeSession(...arguments);
    },

    // Override closePos (Backend button) to block when locked
    closePos() {
        if (this.registerLockState.locked) {
            alert("❌ Register is locked. Ask your manager to unlock it first.");
            return;
        }
        return super.closePos?.(...arguments);
    },
});

// Listen for lock event to start polling on Chrome
document.addEventListener("pos-register-locked", (e) => {
    // The Chrome patch's polling will be triggered via shared state
    sharedLockState.locked = true;
});
