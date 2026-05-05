/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";

/**
 * Patch the POS to color-code KDTY payment buttons.
 * - Cash KDTY  → green  (.cash-kdty-btn)
 * - Card KDTY  → blue   (.card-kdty-btn)
 *
 * The logic runs after every render so it works even when
 * the DOM is rebuilt (e.g. screen transitions).
 */

// ── Helper that stamps CSS classes on every rendered button ──────────────────
function applyKdtyButtonColors() {
    // Target both the numpad-style one-click buttons AND the regular
    // payment-method buttons that appear in the payment screen.
    const selectors = [
        ".payment-method-button",   // Odoo 17-19 payment screen buttons
        ".pos-payment-button",      // alternative class used in some builds
        ".o_payment_method",        // older class
        "button",                   // broad fallback – filtered by text below
    ];

    const allButtons = document.querySelectorAll(selectors.join(","));

    allButtons.forEach((btn) => {
        const label = (btn.textContent || btn.innerText || "").trim().toUpperCase();

        if (label.includes("CASH KDTY") || label.includes("CASH_KDTY")) {
            btn.classList.remove("card-kdty-btn");
            btn.classList.add("cash-kdty-btn");
        } else if (label.includes("CARD KDTY") || label.includes("CARD_KDTY")) {
            btn.classList.remove("cash-kdty-btn");
            btn.classList.add("card-kdty-btn");
        }
    });
}

// ── Observe DOM mutations so new buttons are styled immediately ───────────────
function setupObserver() {
    const observer = new MutationObserver(() => {
        applyKdtyButtonColors();
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true,
    });

    // Initial pass
    applyKdtyButtonColors();
}

// ── Bootstrap after the POS app has mounted ──────────────────────────────────
// We patch PaymentScreenPaymentLines (always rendered in payment flow)
// as a reliable hook; the observer takes care of the rest.
patch(PaymentScreenPaymentLines.prototype, {
    setup() {
        super.setup(...arguments);
    },

    mounted() {
        if (super.mounted) super.mounted(...arguments);
        applyKdtyButtonColors();
    },

    patched() {
        if (super.patched) super.patched(...arguments);
        applyKdtyButtonColors();
    },
});

// Start the global DOM observer once the window loads
window.addEventListener("load", () => {
    setupObserver();
});

// Also run immediately in case the module loads after the page
applyKdtyButtonColors();
