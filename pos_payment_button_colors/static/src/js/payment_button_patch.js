/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";

function colorKdtyButtons() {
    document.querySelectorAll("button, .btn").forEach((btn) => {
        const text = (btn.textContent || "").trim().toUpperCase();

        if (text.includes("CASH KDTY")) {
            // Force green via setAttribute so nothing can override
            btn.setAttribute("style",
                "background: #27ae60 !important;" +
                "background-color: #27ae60 !important;" +
                "color: #fff !important;" +
                "border: 2px solid #1e8449 !important;" +
                "border-bottom: 4px solid #145a30 !important;" +
                "border-radius: 8px !important;" +
                "font-weight: 800 !important;" +
                "box-shadow: 0 4px 10px rgba(39,174,96,0.5) !important;"
            );
        } else if (text.includes("CARD KDTY")) {
            // Force blue via setAttribute so nothing can override
            btn.setAttribute("style",
                "background: #1565c0 !important;" +
                "background-color: #1565c0 !important;" +
                "color: #fff !important;" +
                "border: 2px solid #0d47a1 !important;" +
                "border-bottom: 4px solid #083280 !important;" +
                "border-radius: 8px !important;" +
                "font-weight: 800 !important;" +
                "box-shadow: 0 4px 10px rgba(21,101,192,0.5) !important;"
            );
        }
    });
}

// Run on every DOM change
new MutationObserver(colorKdtyButtons).observe(document.documentElement, {
    childList: true,
    subtree: true,
});

// Run immediately and after load
colorKdtyButtons();
window.addEventListener("load", colorKdtyButtons);
window.addEventListener("DOMContentLoaded", colorKdtyButtons);

patch(PaymentScreenPaymentLines.prototype, {
    setup() { super.setup(...arguments); },
    mounted() { if (super.mounted) super.mounted(...arguments); colorKdtyButtons(); },
    patched() { if (super.patched) super.patched(...arguments); colorKdtyButtons(); },
});
