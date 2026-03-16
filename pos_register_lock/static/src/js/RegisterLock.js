/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { useState, onWillDestroy, onMounted } from "@odoo/owl";
import { Chrome } from "@point_of_sale/app/pos_app";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";

/**
 * Each POS instance gets its OWN lock state keyed by session ID.
 * This prevents one session's lock from bleeding into another.
 */
const lockStateBySession = {};

function getLockState(sessionId) {
    if (!lockStateBySession[sessionId]) {
        lockStateBySession[sessionId] = { locked: false };
    }
    return lockStateBySession[sessionId];
}

patch(Chrome.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        // registerLockState is initialized empty; filled in onMounted once we have session ID
        this.registerLockState = useState({ locked: false });
        this._lockPollInterval = null;

        onMounted(async () => {
            const sessionId = this.pos?.session?.id;
            if (!sessionId) return;

            // Sync state object with per-session store
            const stored = getLockState(sessionId);
            this.registerLockState.locked = stored.locked;

            // Always check backend on load — survives refresh
            try {
                const result = await this.orm.read(
                    "pos.session", [sessionId], ["register_locked"]
                );
                const isLocked = result?.[0]?.register_locked || false;
                this.registerLockState.locked = isLocked;
                stored.locked = isLocked;
                if (isLocked) this._startLockPolling(sessionId);
            } catch (_) {}

            // Listen for lock events from Navbar patch
            this._onLockEvent = (e) => {
                if (e.detail?.sessionId === sessionId) {
                    this.registerLockState.locked = true;
                    stored.locked = true;
                    this._startLockPolling(sessionId);
                }
            };
            document.addEventListener("pos-register-locked", this._onLockEvent);
        });

        onWillDestroy(() => {
            if (this._lockPollInterval) clearInterval(this._lockPollInterval);
            if (this._onLockEvent) {
                document.removeEventListener("pos-register-locked", this._onLockEvent);
            }
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
                    getLockState(sessionId).locked = false;
                    clearInterval(this._lockPollInterval);
                    this._lockPollInterval = null;
                }
            } catch (_) {}
        }, 5000);
    },
});

patch(Navbar.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
    },

    async lockRegister() {
        const sessionId = this.pos?.session?.id;
        if (!sessionId) return;
        try {
            await this.orm.call("pos.session", "action_lock_register", [[sessionId]]);
            getLockState(sessionId).locked = true;
            document.dispatchEvent(new CustomEvent("pos-register-locked", {
                detail: { sessionId }
            }));
        } catch (e) {
            console.error("[RegisterLock] Lock failed:", e);
        }
    },

    closeSession() {
        const sessionId = this.pos?.session?.id;
        if (sessionId && getLockState(sessionId).locked) {
            alert("❌ Register is locked.\nAsk your manager to unlock it from the Odoo backend first.");
            return;
        }
        return super.closeSession(...arguments);
    },

    closePos() {
        const sessionId = this.pos?.session?.id;
        if (sessionId && getLockState(sessionId).locked) {
            alert("❌ Register is locked.\nAsk your manager to unlock it from the Odoo backend first.");
            return;
        }
        return super.closePos?.(...arguments);
    },
});
