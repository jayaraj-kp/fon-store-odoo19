/** @odoo-module **/

import { session } from "@web/session";
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

/**
 * Auto Logout Service for Odoo 19
 * --------------------------------
 * Tracks user inactivity and automatically logs them out
 * after a server-configured timeout.
 *
 * - Fetches timeout from /auto_logout/config (JSON-RPC)
 * - Resets timer on: mousemove, mousedown, keydown, scroll, touch, click, wheel
 * - Shows an orange warning banner 1 minute before logout
 * - Redirects to /web/login after timeout
 */

let logoutTimer = null;
let warningTimer = null;
let delayMinutes = 10;

function clearAllTimers() {
    if (logoutTimer) { clearTimeout(logoutTimer); logoutTimer = null; }
    if (warningTimer) { clearTimeout(warningTimer); warningTimer = null; }
}

function removeWarningBanner() {
    const el = document.getElementById("auto_logout_warning_banner");
    if (el) el.remove();
}

function resetTimer() {
    clearAllTimers();
    removeWarningBanner();
    startTimer();
}

function startTimer() {
    if (!delayMinutes || delayMinutes <= 0) return;

    const delayMs = delayMinutes * 60 * 1000;
    const warningMs = delayMs - 60 * 1000; // warn 1 min before

    if (warningMs > 0) {
        warningTimer = browser.setTimeout(showWarningBanner, warningMs);
    }

    logoutTimer = browser.setTimeout(performLogout, delayMs);
}

function showWarningBanner() {
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
        padding: 16px 22px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
        font-family: sans-serif;
        box-shadow: 0 6px 20px rgba(0,0,0,0.35);
        max-width: 360px;
        line-height: 1.6;
        cursor: pointer;
    `;
    banner.innerHTML = `
        ⚠️ <strong>Inactivity Warning</strong><br>
        <span style="font-weight:400;">
            You will be logged out in <strong>1 minute</strong> due to inactivity.<br>
            Click anywhere to stay logged in.
        </span>
    `;
    banner.addEventListener("click", resetTimer);
    document.body.appendChild(banner);

    // Remove banner after 55s (logout fires at 60s)
    setTimeout(removeWarningBanner, 55000);
}

function performLogout() {
    removeWarningBanner();
    console.info("[AutoLogout] Session expired. Logging out...");

    // Show overlay before redirect
    const overlay = document.createElement("div");
    overlay.style.cssText = `
        position: fixed; inset: 0; z-index: 999999;
        background: rgba(0,0,0,0.65);
        display: flex; align-items: center; justify-content: center;
        color: #fff; font-size: 18px; font-family: sans-serif; font-weight: 600;
    `;
    overlay.textContent = "Session expired due to inactivity. Redirecting to login...";
    document.body.appendChild(overlay);

    setTimeout(() => {
        browser.location.href = "/web/session/logout?redirect=/web/login";
    }, 1500);
}

async function fetchAutoLogoutConfig() {
    try {
        const response = await fetch("/auto_logout/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ jsonrpc: "2.0", method: "call", id: 1, params: {} }),
        });
        const data = await response.json();
        if (data && data.result && typeof data.result.delay === "number") {
            return data.result.delay;
        }
    } catch (err) {
        console.warn("[AutoLogout] Could not fetch config, using default 10 min.", err);
    }
    return 10;
}

async function initAutoLogout() {
    // Only for authenticated users
    if (!session.uid) return;

    delayMinutes = await fetchAutoLogoutConfig();

    if (!delayMinutes || delayMinutes <= 0) {
        console.info("[AutoLogout] Disabled (delay = 0).");
        return;
    }

    const activityEvents = [
        "mousemove", "mousedown", "keydown", "keypress",
        "scroll", "touchstart", "touchmove", "click", "wheel",
    ];
    activityEvents.forEach((evt) => {
        document.addEventListener(evt, resetTimer, { passive: true, capture: true });
    });

    startTimer();
    console.info(`[AutoLogout] Active — timeout: ${delayMinutes} minute(s) of inactivity.`);
}

// Register as an Odoo web service
registry.category("services").add("auto_logout", {
    name: "auto_logout",
    start() {
        initAutoLogout();
    },
});
