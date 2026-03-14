/** @odoo-module **/

import { patch } from "@web/core/utils/patch";

/**
 * In Odoo 19 CE the OrderRow component lives at:
 *   @point_of_sale/app/screens/ticket_screen/order_row
 *
 * We patch its prototype to expose a helper getter that the
 * XML template can call as  paymentMethodNames.
 */
import { OrderRow } from "@point_of_sale/app/screens/ticket_screen/order_row";

patch(OrderRow.prototype, {
    get paymentMethodNames() {
        const order = this.props.order;
        if (!order) return "—";

        // Synced/stored orders expose payment_ids (array of payment records)
        if (order.payment_ids && order.payment_ids.length > 0) {
            const names = order.payment_ids.map((p) => {
                const method = p.payment_method_id;
                if (!method) return "Unknown";
                return method.name || method.display_name || "Unknown";
            });
            return [...new Set(names)].join(", ");
        }

        // Live (not-yet-synced) orders use paymentlines
        if (order.paymentlines && order.paymentlines.length > 0) {
            const names = order.paymentlines.map((line) =>
                line.payment_method?.name || "Unknown"
            );
            return [...new Set(names)].join(", ");
        }

        return "—";
    },
});
