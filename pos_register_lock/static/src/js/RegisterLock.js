/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { useState, onWillDestroy, onMounted } from "@odoo/owl";
import { Chrome } from "@point_of_sale/app/pos_app";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";

// Shared reactive lock state — both Chrome and Navbar share this
// We store it on window so both patches can access it
function getSharedLockState() {
    if (!window.__posRegisterLockState) {
        window.__posRegisterLockState = { locked: false };
    }
    return window.__posRegisterLockState;
}

/**
 * Patch Chrome to:
 * 1. Own the lock state and polling logic
 * 2. Render the full-screen overlay when locked
 */
patch(Chrome.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        // Use useState on shared object so Navbar patch can read it
        this.registerLockState = useState(getSharedLockState());
        this._lockPollInterval = null;

        onMounted(() => {
            if (this.pos?.session?.register_locked) {
                this.registerLockState.locked = true;
                this._startLockPolling();
            }
        });

        onWillDestroy(() => {
            if (this._lockPollInterval) clearInterval(this._lockPollInterval);
        });
    },

    _startLockPolling() {
        if (this._lockPollInterval) clearInterval(this._lockPollInterval);
        this._lockPollInterval = setInterval(async () => {
            try {
                const result = await this.orm.read(
                    "pos.session", [this.pos.session.id], ["register_locked"]
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
 * Patch Navbar to add the lockRegister() method
 * called by the DropdownItem in the burger menu.
 */
patch(Navbar.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.registerLockState = useState(getSharedLockState());
    },

    async lockRegister() {
        try {
            await this.orm.call("pos.session", "action_lock_register", [[this.pos.session.id]]);
            this.registerLockState.locked = true;
            // Trigger polling on Chrome if available
            if (window.__chromeLockStart) window.__chromeLockStart();
        } catch (e) {
            console.error("[RegisterLock] Lock failed:", e);
        }
    },
});

// Expose Chrome polling starter after Chrome setup
const origChromeSetup = Chrome.prototype.setup;
patch(Chrome.prototype, {
    setup() {
        super.setup(...arguments);
        window.__chromeLockStart = () => this._startLockPolling?.();
    },
});
