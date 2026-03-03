/** @odoo-module **/
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { patch } from "@web/core/utils/patch";

patch(OrderReceipt.prototype, {
    get receiptCompany() {
        return this.order?.company || {};
    },
    get receiptPartner() {
        return this.order?.partner_id || null;
    },
    get receiptCashier() {
        try { return this.order?.getCashierName?.() || ""; } catch { return ""; }
    },
    get receiptDate() {
        try { return this.order?.formatDateOrTime?.("date_order") || ""; } catch { return ""; }
    },
    get receiptRef() {
        return this.order?.pos_reference || this.order?.name || "";
    },
});