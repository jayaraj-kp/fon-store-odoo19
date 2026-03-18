/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { useState, onWillDestroy, onMounted } from "@odoo/owl";
import { Chrome } from "@point_of_sale/app/pos_app";
import { ClosePosPopup } from "@point_of_sale/app/components/popups/close_pos_popup/close_pos_popup";

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
// Patch ClosePosPopup — intercept "Close Register" button click
// When cashier clicks Close Register:
//   1. Lock the session in the backend (auto-lock)
//   2. Make all inputs read-only so cashier cannot change amounts
//   3. Show a banner: "Locked for manager review"
//   4. Manager unlocks from backend → poll clears the lock → cashier can close
// ---------------------------------------------------------------------------
patch(ClosePosPopup.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.closingLockState = useState({
            locked: false,
            checking: false,
        });
        this._mySessionId = null;
        this._closePollInterval = null;

        onMounted(async () => {
            this._mySessionId = this.pos?.session?.id;
            if (!this._mySessionId) return;

            // If the popup opens while session is already locked
            // (e.g. after page reload), reflect that
            try {
                const result = await this.orm.read(
                    "pos.session", [this._mySessionId], ["register_locked"]
                );
                if (result?.[0]?.register_locked) {
                    this.closingLockState.locked = true;
                    this._startClosePollForUnlock();
                }
            } catch (_) {}
        });

        onWillDestroy(() => {
            if (this._closePollInterval) clearInterval(this._closePollInterval);
        });
    },

    /**
     * Override the default close action.
     * First time: lock and show read-only view.
     * If already unlocked by manager: proceed to close normally.
     */
    async closeSession() {
        const sessionId = this.pos?.session?.id;
        if (!sessionId) return super.closeSession(...arguments);

        // If already locked, check if manager has unlocked yet
        if (this.closingLockState.locked) {
            this.closingLockState.checking = true;
            try {
                const result = await this.orm.read(
                    "pos.session", [sessionId], ["register_locked"]
                );
                if (result?.[0]?.register_locked === false) {
                    // Manager has unlocked — proceed with actual close
                    this.closingLockState.locked = false;
                    return super.closeSession(...arguments);
                } else {
                    alert(
                        "⏳ Register is still locked.\n\n" +
                        "Your manager needs to review the excess/short amounts.\n" +
                        "Ask them to go to:\n" +
                        "Point of Sale → Sessions → Unlock Register\n\n" +
                        "The screen will update automatically when unlocked."
                    );
                }
            } catch (_) {
                return super.closeSession(...arguments);
            } finally {
                this.closingLockState.checking = false;
            }
            return;
        }

        // First click: auto-lock and show read-only view
        try {
            await this.orm.call(
                "pos.session", "action_lock_register", [[sessionId]]
            );
            this.closingLockState.locked = true;

            // Notify Chrome overlay via event
            document.dispatchEvent(new CustomEvent("pos-register-locked", {
                detail: { sessionId: sessionId }
            }));

            // Start polling inside the popup too
            this._startClosePollForUnlock();

        } catch (e) {
            console.error("[RegisterLock] Auto-lock on close failed:", e);
            // If lock fails, still allow close to prevent cashier being stuck
            return super.closeSession(...arguments);
        }
    },

    /**
     * Poll backend every 5s. When unlocked, update popup state
     * so the cashier sees the "Close Register" button become active again.
     */
    _startClosePollForUnlock() {
        if (this._closePollInterval) clearInterval(this._closePollInterval);
        const sessionId = this._mySessionId;
        this._closePollInterval = setInterval(async () => {
            try {
                const result = await this.orm.read(
                    "pos.session", [sessionId], ["register_locked"]
                );
                if (result?.[0]?.register_locked === false) {
                    this.closingLockState.locked = false;
                    clearInterval(this._closePollInterval);
                    this._closePollInterval = null;
                }
            } catch (_) {}
        }, 5000);
    },
});
