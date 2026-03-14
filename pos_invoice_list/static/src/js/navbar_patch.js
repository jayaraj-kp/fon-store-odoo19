/** @odoo-module **/

import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { patch } from "@web/core/utils/patch";

patch(Navbar.prototype, {
    onClickInvoices() {
        this.pos.navigate("InvoiceScreen");
    },

    get mainButton() {
        const screens = ["ProductScreen", "PaymentScreen", "ReceiptScreen", "TipScreen"];
        const current = this.pos.router.state.current;
        if (current === "InvoiceScreen") return "invoices";
        return screens.includes(current) ? "register" : "order";
    },
});
