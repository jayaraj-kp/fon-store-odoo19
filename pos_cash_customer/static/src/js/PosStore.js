/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    /**
     * After POS data is loaded, find and store the CASH CUSTOMER partner id
     * so all components can access it easily.
     */
    async setup() {
        await super.setup(...arguments);
    },

    async _processData(loadedData) {
        await super._processData(loadedData);
        this._setCashCustomer();
    },

    _setCashCustomer() {
        const partners = this.models["res.partner"]?.getAll() || [];
        const cashCustomer = partners.find((p) => p.is_cash_customer === true);
        this.cashCustomerPartner = cashCustomer || null;
        if (cashCustomer) {
            console.log(
                `[POS Cash Customer] Master CASH CUSTOMER loaded: id=${cashCustomer.id}`
            );
        } else {
            console.warn("[POS Cash Customer] CASH CUSTOMER partner not found in POS data.");
        }
    },

    /**
     * Returns the master CASH CUSTOMER partner object.
     */
    getCashCustomer() {
        return this.cashCustomerPartner || null;
    },
});
