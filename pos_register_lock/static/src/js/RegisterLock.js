/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { useState, onWillDestroy, onMounted } from "@odoo/owl";
import { Chrome } from "@point_of_sale/app/pos_app";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";

// ---------------------------------------------------------------------------
// Patch Chrome — restore lock state on page load + poll for unlock
// ---------------------------------------------------------------------------
patch(Chrome.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.registerLockState = useState({ locked: false });
        this._lockPollInterval = null;
        this._mySessionId = null;

        onMounted(async () => {
            this._mySessionId = this.pos?.session?.id;
            if (!this._mySessionId) return;

            // Restore lock state after page refresh
            try {
                const result = await this.orm.read(
                    "pos.session", [this._mySessionId], ["register_locked"]
                );
                const isLocked = result?.[0]?.register_locked || false;
                this.registerLockState.locked = isLocked;
                if (isLocked) this._startLockPolling();
            } catch (_) {}

            // Listen for lock events fired in the same browser tab
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

    /**
     * Poll the backend every 5 seconds until the manager unlocks.
     * Once unlocked, remove the overlay so the cashier can proceed.
     */
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
                    // Notify cashier that they can now close
                    this.env.services.notification?.add(
                        "✅ Register unlocked by manager. You may now close the session.",
                        { type: "success", sticky: false }
                    );
                }
            } catch (_) {}
        }, 5000);
    },
});

// ---------------------------------------------------------------------------
// Patch Navbar — intercept closeSession / closePos to auto-lock first
// ---------------------------------------------------------------------------
patch(Navbar.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
    },

    /**
     * Called when the cashier clicks "Close" from the navbar.
     * First click: auto-lock the session so amounts are frozen, show overlay.
     * Subsequent clicks (while locked): warn cashier to wait for manager.
     * After manager unlocks: proceed to close normally.
     */
    async closeSession() {
        const sessionId = this.pos?.session?.id;
        if (!sessionId) return super.closeSession(...arguments);

        try {
            const result = await this.orm.read(
                "pos.session", [sessionId], ["register_locked"]
            );
            const isLocked = result?.[0]?.register_locked;

            if (isLocked) {
                // Already locked — manager hasn't unlocked yet
                alert(
                    "⏳ Register is locked for manager review.\n\n" +
                    "Ask your manager to go to:\n" +
                    "Point of Sale \u2192 Sessions \u2192 Unlock Register\n\n" +
                    "The screen will update automatically when unlocked."
                );
                return;
            }

            // Not locked yet — auto-lock now and show overlay
            await this.orm.call(
                "pos.session", "action_lock_register", [[sessionId]]
            );

            // Trigger Chrome full-screen overlay
            document.dispatchEvent(new CustomEvent("pos-register-locked", {
                detail: { sessionId: sessionId }
            }));

        } catch (e) {
            console.error("[RegisterLock] Error during close intercept:", e);
            // On error, fall through to normal close to avoid cashier being stuck
            return super.closeSession(...arguments);
        }
    },

    /**
     * Also intercept closePos (hamburger \u2192 Close) with the same logic.
     */
    async closePos() {
        const sessionId = this.pos?.session?.id;
        if (!sessionId) return super.closePos?.(...arguments);

        try {
            const result = await this.orm.read(
                "pos.session", [sessionId], ["register_locked"]
            );
            const isLocked = result?.[0]?.register_locked;

            if (isLocked) {
                alert(
                    "⏳ Register is locked for manager review.\n\n" +
                    "Ask your manager to go to:\n" +
                    "Point of Sale \u2192 Sessions \u2192 Unlock Register\n\n" +
                    "The screen will update automatically when unlocked."
                );
                return;
            }

            // Lock first, then show overlay
            await this.orm.call(
                "pos.session", "action_lock_register", [[sessionId]]
            );
            document.dispatchEvent(new CustomEvent("pos-register-locked", {
                detail: { sessionId: sessionId }
            }));

        } catch (e) {
            console.error("[RegisterLock] Error during closePos intercept:", e);
            return super.closePos?.(...arguments);
        }
    },
});
