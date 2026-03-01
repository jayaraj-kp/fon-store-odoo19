(function () {
    "use strict";

    // ─── State ───────────────────────────────────────────────────────────────
    var logoutTimer  = null;
    var warningTimer = null;
    var delayMinutes = 10;
    var initialized  = false;

    // ─── Helpers ─────────────────────────────────────────────────────────────
    function clearAllTimers() {
        if (logoutTimer)  { clearTimeout(logoutTimer);  logoutTimer  = null; }
        if (warningTimer) { clearTimeout(warningTimer); warningTimer = null; }
    }

    function removeBanner() {
        var el = document.getElementById("al_warning_banner");
        if (el) { el.parentNode.removeChild(el); }
    }

    function resetTimer() {
        clearAllTimers();
        removeBanner();
        startTimer();
    }

    function startTimer() {
        if (!delayMinutes || delayMinutes <= 0) { return; }

        var delayMs   = delayMinutes * 60 * 1000;
        var warningMs = delayMs - 60 * 1000;   // 1 min before logout

        if (warningMs > 0) {
            warningTimer = setTimeout(showBanner, warningMs);
        } else {
            // delay <= 1 min: show banner immediately
            showBanner();
        }
        logoutTimer = setTimeout(doLogout, delayMs);
    }

    function showBanner() {
        removeBanner();
        var d = document.createElement("div");
        d.id = "al_warning_banner";
        d.style.cssText = [
            "position:fixed",
            "top:20px",
            "right:20px",
            "z-index:2147483647",
            "background:linear-gradient(135deg,#ff9800,#f44336)",
            "color:#fff",
            "padding:16px 22px",
            "border-radius:8px",
            "font-size:14px",
            "font-weight:600",
            "font-family:sans-serif",
            "box-shadow:0 6px 20px rgba(0,0,0,0.4)",
            "max-width:380px",
            "line-height:1.7",
            "cursor:pointer",
        ].join(";");
        d.innerHTML = (
            "\u26A0\uFE0F <strong>Inactivity Warning</strong><br>" +
            "<span style='font-weight:400'>" +
            "You will be logged out in <strong>1 minute</strong>.<br>" +
            "Click anywhere to stay logged in." +
            "</span>"
        );
        d.addEventListener("click", resetTimer);
        document.body.appendChild(d);
        setTimeout(removeBanner, 55000);
    }

    function doLogout() {
        removeBanner();
        console.info("[AutoLogout] Logging out due to inactivity.");

        var overlay = document.createElement("div");
        overlay.style.cssText = [
            "position:fixed",
            "top:0","left:0","right:0","bottom:0",
            "z-index:2147483647",
            "background:rgba(0,0,0,0.7)",
            "display:flex",
            "flex-direction:column",
            "align-items:center",
            "justify-content:center",
            "color:#fff",
            "font-family:sans-serif",
            "gap:12px",
        ].join(";");
        overlay.innerHTML = (
            "<div style='font-size:22px;font-weight:700'>\uD83D\uDD12 Session Expired</div>" +
            "<div style='font-size:15px;opacity:0.85'>Redirecting to login page...</div>"
        );
        document.body.appendChild(overlay);

        setTimeout(function () {
            window.location.href = "/web/session/logout?redirect=/web/login";
        }, 1500);
    }

    // ─── Fetch config from server ─────────────────────────────────────────────
    function fetchConfig(callback) {
        var xhr = new XMLHttpRequest();
        xhr.open("POST", "/auto_logout/config", true);
        xhr.setRequestHeader("Content-Type", "application/json");
        xhr.onreadystatechange = function () {
            if (xhr.readyState === 4) {
                try {
                    var data = JSON.parse(xhr.responseText);
                    if (data && data.result && typeof data.result.delay === "number") {
                        callback(data.result.delay);
                        return;
                    }
                } catch (e) {}
                callback(10); // fallback
            }
        };
        xhr.send(JSON.stringify({ jsonrpc: "2.0", method: "call", id: 1, params: {} }));
    }

    // ─── Bind activity events ─────────────────────────────────────────────────
    function bindEvents() {
        var events = [
            "mousemove","mousedown","keydown",
            "scroll","touchstart","touchmove","click","wheel"
        ];
        for (var i = 0; i < events.length; i++) {
            document.addEventListener(events[i], resetTimer, { passive: true, capture: true });
        }
    }

    // ─── Init ─────────────────────────────────────────────────────────────────
    function init() {
        if (initialized) { return; }

        // Skip only on login/signup pages
        var path = window.location.pathname;
        var isLoginPage = (
            path === "/web/login" ||
            path === "/web/signup" ||
            path === "/web/reset_password" ||
            path.indexOf("/web/login") !== -1
        );

        if (isLoginPage) {
            console.info("[AutoLogout] Login page — skipping.");
            return;
        }

        fetchConfig(function (delay) {
            delayMinutes = delay;

            if (!delayMinutes || delayMinutes <= 0) {
                console.info("[AutoLogout] Disabled (delay = 0).");
                return;
            }

            initialized = true;
            bindEvents();
            startTimer();
            console.info("[AutoLogout] \u2705 Active — logout after " + delayMinutes + " min of inactivity.");
        });
    }

    // ─── Wait for page to be ready, then init ────────────────────────────────
    // Use multiple triggers to ensure we catch Odoo's SPA navigation too
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }

    // Also re-init on Odoo SPA route changes (covers page navigation within Odoo)
    window.addEventListener("hashchange", function () {
        if (!initialized) { init(); }
    });

    // Fallback: retry after 3 seconds in case Odoo loads late
    setTimeout(function () {
        if (!initialized) {
            console.info("[AutoLogout] Retrying init...");
            init();
        }
    }, 3000);

    // Expose for debugging
    window.__autoLogout = {
        status: function () {
            return {
                initialized: initialized,
                delayMinutes: delayMinutes,
                logoutTimerActive: !!logoutTimer,
                warningTimerActive: !!warningTimer,
            };
        },
        forceLogout: doLogout,
        reset: resetTimer,
    };

})();
