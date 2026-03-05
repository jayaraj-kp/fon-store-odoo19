/** @odoo-module **/

/**
 * Odoo 19 CE — patch PosStore to cache the CASH CUSTOMER partner
 * after POS data is loaded.
 */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.cashCustomerPartner = null;
    },

    /**
     * Called by Odoo 19 POS after all models are loaded.
     * We search the loaded partners for the one flagged is_cash_customer.
     */
    async load(loadedData) {
        await super.load(...arguments);
        this._findCashCustomer();
    },

    _findCashCustomer() {
        // Odoo 19: models stored in this.models["res.partner"]
        const partnerModel = this.models["res.partner"];
        const partners = partnerModel ? partnerModel.getAll() : [];
        this.cashCustomerPartner = partners.find((p) => p.is_cash_customer) || null;

        if (this.cashCustomerPartner) {
            console.log(
                `[POS Cash Customer] ✅ CASH CUSTOMER loaded: id=${this.cashCustomerPartner.id}`
            );
        } else {
            console.warn(
                "[POS Cash Customer] ⚠️ CASH CUSTOMER not found. " +
                "Make sure the module is installed and POS session is restarted."
            );
        }
    },

    /** Public getter used by other patches and templates */
    getCashCustomer() {
        return this.cashCustomerPartner || null;
    },
});
