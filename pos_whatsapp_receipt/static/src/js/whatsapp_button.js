/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { usePos } from "@point_of_sale/app/store/pos_hook";

// ────────────────────────────────────────────────────────────
//  Patch Receipt Screen: add "Send on WhatsApp" button
// ────────────────────────────────────────────────────────────

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.whatsappState = useState({ sending: false, sent: false, error: "" });
    },

    async sendWhatsappReceipt() {
        const order = this.pos.get_order();
        if (!order) return;

        // Get phone from current order's partner
        const partner = order.get_partner();
        const phone = partner ? (partner.mobile || partner.phone) : null;

        if (!phone) {
            this.whatsappState.error = "No phone number on customer record.";
            this.notification.add("No phone number found for this customer.", {
                type: "warning",
                title: "WhatsApp",
            });
            return;
        }

        this.whatsappState.sending = true;
        this.whatsappState.error = "";

        try {
            const result = await this.orm.call(
                "pos.order",
                "send_whatsapp_receipt",
                [order.server_id || order.backendId],
                {}
            );

            if (result && result.success) {
                this.whatsappState.sent = true;
                this.notification.add(result.message || "Receipt sent via WhatsApp!", {
                    type: "success",
                    title: "WhatsApp ✓",
                });
            } else {
                this.whatsappState.error = result ? result.message : "Unknown error";
                this.notification.add(this.whatsappState.error, {
                    type: "danger",
                    title: "WhatsApp Failed",
                });
            }
        } catch (e) {
            this.whatsappState.error = e.message || "Error sending WhatsApp message.";
            this.notification.add(this.whatsappState.error, {
                type: "danger",
                title: "WhatsApp Error",
            });
        } finally {
            this.whatsappState.sending = false;
        }
    },
});

// ────────────────────────────────────────────────────────────
//  Extend ReceiptScreen template to show the WA button
//  We inject a method so the XML template can call it.
// ────────────────────────────────────────────────────────────

ReceiptScreen.prototype._getWhatsappButtonLabel = function () {
    if (this.whatsappState.sending) return "⏳ Sending...";
    if (this.whatsappState.sent) return "✅ Sent on WhatsApp";
    return "📲 Send WhatsApp Receipt";
};

ReceiptScreen.prototype._canSendWhatsapp = function () {
    const order = this.pos.get_order();
    if (!order) return false;
    const partner = order.get_partner();
    return !!(partner && (partner.mobile || partner.phone));
};
