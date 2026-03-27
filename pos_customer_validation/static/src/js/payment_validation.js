/** @odoo-module */

console.log("✅ POS Customer Validation JS LOADED");

/**
 * This script blocks:
 * - Cash KDTY
 * - Card KDTY
 * (fast-pay-button / one-click payments)
 * if NO customer is selected
 */

(function () {

    function getPosInstance() {
        try {
            const posRoot = document.querySelector(".pos");

            if (!posRoot || !posRoot.__owl__) {
                console.log("❌ POS root or OWL not found");
                return null;
            }

            let comp = posRoot.__owl__;

            // Walk up component tree to find env.pos
            while (comp && !comp.env?.pos) {
                comp = comp.parent;
            }

            if (!comp || !comp.env?.pos) {
                console.log("❌ POS instance not found");
                return null;
            }

            return comp.env.pos;

        } catch (err) {
            console.log("ERROR getting POS:", err);
            return null;
        }
    }

    function handleFastPayClick(event) {
        const button = event.target.closest(".fast-pay-button");

        if (!button) return;

        console.log("🔥 Fast Pay Click:", button.innerText);

        const pos = getPosInstance();

        if (!pos) return;

        const order = pos.get_order();
        if (!order) return;

        const customer = order.get_partner();

        console.log("👤 Customer:", customer);

        // 🔴 BLOCK if no customer
        if (!customer) {
            console.log("⛔ Blocking payment - No customer");

            event.preventDefault();
            event.stopPropagation();

            alert("⚠️ Please select a customer before proceeding with payment.");

            return false;
        }

        console.log("✅ Customer found, allow payment");
    }

    // Attach global click listener
    document.addEventListener("click", handleFastPayClick);

})();