/** @odoo-module **/
import { useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.whatsappState = useState({ sending: false, sent: false, error: "" });
    },

    async sendWhatsappReceipt() {
        const order = this.pos.get_order();
        if (!order) return;
        const partner = order.get_partner();
        const phone = partner ? (partner.mobile || partner.phone) : null;
        if (!phone) {
            this.notification.add("No phone number found for this customer.", { type: "warning", title: "WhatsApp" });
            return;
        }
        this.whatsappState.sending = true;
        this.whatsappState.error = "";
        try {
            const orderId = order.server_id || order.id;
            const result = await this.orm.call("pos.order", "send_whatsapp_receipt", [orderId], {});
            if (result && result.success) {
                this.whatsappState.sent = true;
                this.notification.add(result.message || "Receipt sent!", { type: "success", title: "WhatsApp ✓" });
            } else {
                this.whatsappState.error = result ? result.message : "Unknown error";
                this.notification.add(this.whatsappState.error, { type: "danger", title: "WhatsApp Failed" });
            }
        } catch (e) {
            this.whatsappState.error = e.message || "Error sending message.";
            this.notification.add(this.whatsappState.error, { type: "danger", title: "WhatsApp Error" });
        } finally {
            this.whatsappState.sending = false;
        }
    },
});
