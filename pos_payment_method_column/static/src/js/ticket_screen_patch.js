/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

patch(TicketScreen.prototype, {
    /**
     * Returns a comma-separated list of payment method names for the given order.
     * Reads from payment_ids (synced orders) or paymentlines (live orders).
     */
    getPaymentMethod(order) {
        if (!order) return "—";

        // Synced/stored orders: payment_ids is an array of pos.payment records
        if (order.payment_ids && order.payment_ids.length > 0) {
            const names = order.payment_ids.map((p) => {
                const method = p.payment_method_id;
                if (!method) return "Unknown";
                return method.name || method.display_name || "Unknown";
            });
            return [...new Set(names)].join(", ");
        }

        // Live (not-yet-synced) orders: paymentlines on the order object
        if (order.paymentlines && order.paymentlines.length > 0) {
            const names = order.paymentlines.map((line) =>
                line.payment_method?.name || "Unknown"
            );
            return [...new Set(names)].join(", ");
        }

        return "—";
    },
});
