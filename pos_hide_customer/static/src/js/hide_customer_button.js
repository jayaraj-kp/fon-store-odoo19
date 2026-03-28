/** @odoo-module */

// Hide Customer (.set-partner) button in POS - Odoo 19

function hideCustomerButton() {
    const btn = document.querySelector('.set-partner');
    if (btn) {
        btn.style.display = 'none';
        console.log('[pos_hide_customer] ✅ Customer button hidden');
    }
}

function startObserver() {
    hideCustomerButton();

    const observer = new MutationObserver(function () {
        hideCustomerButton();
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true,
    });

    console.log('[pos_hide_customer] ✅ MutationObserver active');
}

// Wait for DOM to be fully ready before observing
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startObserver);
} else {
    startObserver();
}