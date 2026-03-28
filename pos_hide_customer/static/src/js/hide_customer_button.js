/** @odoo-module */

// Hide Customer (.set-partner) button in POS - Odoo 19
// Uses MutationObserver to catch the button as soon as it renders

function hideCustomerButton() {
    const btn = document.querySelector('.set-partner');
    if (btn) {
        btn.style.display = 'none';
        console.log('[pos_hide_customer] ✅ Customer button hidden');
    }
}

// Run immediately in case DOM is already ready
hideCustomerButton();

// Watch for DOM changes (POS is a SPA, button may render later)
const observer = new MutationObserver(function () {
    hideCustomerButton();
});

observer.observe(document.body, {
    childList: true,
    subtree: true,
});

console.log('[pos_hide_customer] ✅ MutationObserver active');