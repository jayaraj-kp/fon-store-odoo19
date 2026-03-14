/** @odoo-module **/

import { OrderRow } from "@point_of_sale/app/screens/ticket_screen/order_row/order_row";
import { patch } from "@web/core/utils/patch";

patch(OrderRow.prototype, {
    /**
     * Returns a comma-separated string of payment method names used in this order.
     * Falls back to '—' if no payment info is available.
     */
    get paymentMethodNames() {
        const order = this.props.order;

        // Odoo 19 CE: payment lines are in order.payment_ids
        if (order.payment_ids && order.payment_ids.length > 0) {
            const names = order.payment_ids.map((payment) => {
                // payment_method_id is a Many2one → {id, display_name} in JSON
                if (payment.payment_method_id) {
                    return payment.payment_method_id.name || payment.payment_method_id.display_name || "Unknown";
                }
                return "Unknown";
            });
            // Deduplicate (e.g. two cash payments → show "Cash" once)
            return [...new Set(names)].join(", ");
        }

        // Fallback: try paymentlines on a live (not-yet-synced) order object
        if (order.paymentlines && order.paymentlines.length > 0) {
            const names = order.paymentlines.map((line) => {
                if (line.payment_method) {
                    return line.payment_method.name;
                }
                return "Unknown";
            });
            return [...new Set(names)].join(", ");
        }

        return "—";
    },
});
