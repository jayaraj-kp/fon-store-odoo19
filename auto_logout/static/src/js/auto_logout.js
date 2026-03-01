/** @odoo-module **/

import { session } from "@web/session";
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

/**
 * Auto Logout Service
 * -------------------
 * Tracks user inactivity and automatically logs them out after a configured timeout.
 * - Fetches timeout config from the server via JSON-RPC
 * - Resets timer on any user activity (mouse, keyboard, scroll, touch, click)
 * - Shows an orange warning banner 1 minute before logout
 * - Redirects to /web/login on timeout
 */

let logoutTimer = null;
let warningTimer = null;
let delayMinutes = 10;

function clearAllTimers() {
    if (logoutTimer) {
        clearTimeout(logoutTimer);
        logoutTimer = null;
    }
    if (warningTimer) {
        clearTimeout(warningTimer);
        warningTimer = null;
    }
}

function resetTimer() {
    clearAllTimers();
    removeWarningBanner();
    startTimer();
}

function startTimer() {
    if (!delayMinutes || delayMinutes <= 0) return;

    const delayMs = delayMinutes * 60 * 1000;
    const warningMs = delayMs - 60 * 1000; // Show warning 1 minute before logout

    if (warningMs > 0) {
        warningTimer = browser.setTimeout(() => {
            showWarningBanner();
        }, warningMs);
    }

    logoutTimer = browser.setTimeout(() => {
        performLogout();
    }, delayMs);
}

function showWarningBanner() {
    // Remove any existing banner first
    removeWarningBanner();

    const banner = document.createElement("div");
    banner.id = "auto_logout_warning_banner";
    banner.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 100000;
        background: linear-gradient(135deg, #ff9800, #f44336);
        color: #fff;
        padding: 16px 24px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
        font-family: sans-serif;
        box-shadow: 0 6px 20px rgba(0,0,0,0.35);
        max-width: 360px;
        line-height: 1.5;
        cursor: pointer;
        transition: opacity 0.3s ease;
    `;
    banner.innerHTML = `
        ⚠️ <strong>Inactivity Warning</strong><br>
        <span style="font-weight:400;">You will be automatically logged out in <strong>1 minute</strong> due to inactivity.<br>
        Click anywhere to stay logged in.</span>
    `;

    // Clicking the banner itself also resets the timer
    banner.addEventListener("click", () => {
        resetTimer();
    });

    document.body.appendChild(banner);

    // Auto-remove banner after 55 seconds (logout fires at 60s)
    setTimeout(() => {
        removeWarningBanner();
    }, 55000);
}

function removeWarningBanner() {
    const existing = document.getElementById("auto_logout_warning_banner");
    if (existing) {
        existing.remove();
    }
}

function performLogout() {
    removeWarningBanner();
    console.info("[AutoLogout] Session expired due to inactivity. Logging out...");

    // Show a brief logout notice before redirecting
    const overlay = document.createElement("div");
    overlay.style.cssText = `
        position: fixed;
        inset: 0;
        z-index: 999999;
        background: rgba(0,0,0,0.6);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 18px;
        font-family: sans-serif;
        font-weight: 600;
    `;
    overlay.textContent = "Session expired. Redirecting to login...";
    document.body.appendChild(overlay);

    setTimeout(() => {
        browser.location.href = "/web/session/logout?redirect=/web/login";
    }, 1500);
}

async function fetchAutoLogoutConfig() {
    try {
        const response = await fetch("/auto_logout/config", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                id: 1,
                params: {},
            }),
        });
        const data = await response.json();
        if (data && data.result && typeof data.result.delay === "number") {
            return data.result.delay;
        }
    } catch (error) {
        console.warn("[AutoLogout] Failed to fetch config, using default 10 minutes.", error);
    }
    return 10; // default fallback
}

async function initAutoLogout() {
    // Only activate for authenticated users
    if (!session.uid) {
        return;
    }

    delayMinutes = await fetchAutoLogoutConfig();

    if (!delayMinutes || delayMinutes <= 0) {
        console.info("[AutoLogout] Auto logout is disabled (delay = 0).");
        return;
    }

    // Attach activity listeners to reset the inactivity timer
    const activityEvents = [
        "mousemove",
        "mousedown",
        "keydown",
        "keypress",
        "scroll",
        "touchstart",
        "touchmove",
        "click",
        "wheel",
    ];

    activityEvents.forEach((eventName) => {
        document.addEventListener(eventName, resetTimer, { passive: true, capture: true });
    });

    // Kick off the timer
    startTimer();

    console.info(
        `[AutoLogout] Initialized. User will be logged out after ${delayMinutes} minute(s) of inactivity.`
    );
}

// Register as an Odoo web service so it starts with the web client
const autoLogoutService = {
    name: "auto_logout",
    start() {
        initAutoLogout();
    },
};

registry.category("services").add("auto_logout", autoLogoutService);
