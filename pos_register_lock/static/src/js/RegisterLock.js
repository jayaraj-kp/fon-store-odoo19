/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { useState, onWillDestroy, onMounted } from "@odoo/owl";
import { Chrome } from "@point_of_sale/app/pos_app";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";

patch(Chrome.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.registerLockState = useState({ locked: false });
        this._lockPollInterval = null;
        this._mySessionId = null;

        onMounted(async () => {
            // Store THIS instance's session ID — never cross-check with other sessions
            this._mySessionId = this.pos?.session?.id;
            if (!this._mySessionId) return;

            // Check backend on every load — survives page refresh
            try {
                const result = await this.orm.read(
                    "pos.session", [this._mySessionId], ["register_locked"]
                );
                const isLocked = result?.[0]?.register_locked || false;
                this.registerLockState.locked = isLocked;
                if (isLocked) this._startLockPolling();
            } catch (_) {}

            // Only respond to lock events for THIS session
            this._onLockEvent = (e) => {
                if (e.detail?.sessionId === this._mySessionId) {
                    this.registerLockState.locked = true;
                    this._startLockPolling();
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

    _startLockPolling() {
        if (this._lockPollInterval) clearInterval(this._lockPollInterval);
        const sessionId = this._mySessionId;
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

patch(Navbar.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
    },

    async lockRegister() {
        const sessionId = this.pos?.session?.id;
        if (!sessionId) return;
        try {
            // Lock ONLY this specific session in the backend
            await this.orm.call(
                "pos.session", "action_lock_register", [[sessionId]]
            );
            // Fire event with THIS session's ID only
            // Chrome instances for OTHER sessions will ignore this event
            document.dispatchEvent(new CustomEvent("pos-register-locked", {
                detail: { sessionId: sessionId }
            }));
        } catch (e) {
            console.error("[RegisterLock] Lock failed:", e);
        }
    },

    closeSession() {
        const sessionId = this.pos?.session?.id;
        if (!sessionId) return super.closeSession(...arguments);
        // Check backend lock state before allowing close
        this.orm.read("pos.session", [sessionId], ["register_locked"]).then((result) => {
            if (result?.[0]?.register_locked) {
                alert("❌ Register is locked.\nAsk your manager to unlock it from the Odoo backend first.");
            } else {
                super.closeSession(...arguments);
            }
        }).catch(() => {
            super.closeSession(...arguments);
        });
    },

    closePos() {
        const sessionId = this.pos?.session?.id;
        if (!sessionId) return super.closePos?.(...arguments);
        this.orm.read("pos.session", [sessionId], ["register_locked"]).then((result) => {
            if (result?.[0]?.register_locked) {
                alert("❌ Register is locked.\nAsk your manager to unlock it from the Odoo backend first.");
            } else {
                super.closePos?.(...arguments);
            }
        }).catch(() => {
            super.closePos?.(...arguments);
        });
    },
});
