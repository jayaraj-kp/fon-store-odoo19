/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { _t } from "@web/core/l10n/translation";

function getOrderProductNames(order) {
    const lines =
        (typeof order.get_orderlines === "function" && order.get_orderlines()) ||
        order.lines || order.orderlines || [];
    return Array.from(lines)
        .map((line) =>
            (typeof line.get_full_product_name === "function" && line.get_full_product_name()) ||
            line.full_product_name || line.product_name ||
            (line.product_id && (line.product_id.display_name || line.product_id.name)) ||
            (line.product && (line.product.display_name || line.product.name)) || ""
        )
        .filter(Boolean).join(" ").toLowerCase();
}

function getOrderPaymentMethods(order) {
    const paymentLines =
        (typeof order.get_paymentlines === "function" && order.get_paymentlines()) ||
        order.payment_ids || order.paymentlines || order.payment_lines || [];
    return Array.from(paymentLines)
        .map((line) =>
            (line.payment_method_id && (line.payment_method_id.name || line.payment_method_id.display_name)) ||
            (line.payment_method && (line.payment_method.name || line.payment_method.display_name)) ||
            line.name || ""
        )
        .filter(Boolean).join(" ").toLowerCase();
}

function getOrderDate(order) {
    // Try all known date fields and return a searchable string
    const raw =
        order.date_order ||
        order.creation_date ||
        order.date ||
        "";
    if (!raw) return "";
    try {
        // Return both the raw value and a formatted date string so
        // user can search "2026", "03/19", "19/03/2026", etc.
        const d = new Date(raw);
        const pad = (n) => String(n).padStart(2, "0");
        const yyyy = d.getFullYear();
        const mm = pad(d.getMonth() + 1);
        const dd = pad(d.getDate());
        // Include multiple formats for flexible matching
        return `${yyyy}-${mm}-${dd} ${dd}/${mm}/${yyyy} ${mm}/${dd}/${yyyy} ${raw}`.toLowerCase();
    } catch (_e) {
        return String(raw).toLowerCase();
    }
}

patch(TicketScreen.prototype, {
    _getSearchFields() {
        let fields = {};
        try { fields = super._getSearchFields() || {}; } catch (_e) {}
        return {
            ...fields,
            PRODUCT: {
                displayName: _t("Product"),
                modelField: "lines.product_id.display_name",
                repr: (order) => getOrderProductNames(order),
            },
            PAYMENT_METHOD: {
                displayName: _t("Payment Method"),
                modelField: "payment_ids.payment_method_id.name",
                repr: (order) => getOrderPaymentMethods(order),
            },
            ORDER_DATE: {
                displayName: _t("Date"),
                modelField: "date_order",
                repr: (order) => getOrderDate(order),
            },
        };
    },

    getSearchFields() {
        let fields = {};
        try { fields = super.getSearchFields() || {}; } catch (_e) {}
        return {
            ...fields,
            PRODUCT: {
                displayName: _t("Product"),
                modelField: "lines.product_id.display_name",
                repr: (order) => getOrderProductNames(order),
            },
            PAYMENT_METHOD: {
                displayName: _t("Payment Method"),
                modelField: "payment_ids.payment_method_id.name",
                repr: (order) => getOrderPaymentMethods(order),
            },
            ORDER_DATE: {
                displayName: _t("Date"),
                modelField: "date_order",
                repr: (order) => getOrderDate(order),
            },
        };
    },

    _doesOrderPassFilter(order, { fieldName, searchTerm }) {
        if (fieldName === "PRODUCT") {
            const term = (searchTerm || "").toLowerCase().trim();
            if (!term) return true;
            return getOrderProductNames(order).includes(term);
        }
        if (fieldName === "PAYMENT_METHOD") {
            const term = (searchTerm || "").toLowerCase().trim();
            if (!term) return true;
            return getOrderPaymentMethods(order).includes(term);
        }
        if (fieldName === "ORDER_DATE") {
            const term = (searchTerm || "").toLowerCase().trim();
            if (!term) return true;
            return getOrderDate(order).includes(term);
        }
        try { return super._doesOrderPassFilter(order, { fieldName, searchTerm }); }
        catch (_e) { return true; }
    },

    filterOrderBySearch(order, searchDetails) {
        if (searchDetails?.fieldName === "PRODUCT") {
            const term = (searchDetails.searchTerm || "").toLowerCase().trim();
            if (!term) return true;
            return getOrderProductNames(order).includes(term);
        }
        if (searchDetails?.fieldName === "PAYMENT_METHOD") {
            const term = (searchDetails.searchTerm || "").toLowerCase().trim();
            if (!term) return true;
            return getOrderPaymentMethods(order).includes(term);
        }
        if (searchDetails?.fieldName === "ORDER_DATE") {
            const term = (searchDetails.searchTerm || "").toLowerCase().trim();
            if (!term) return true;
            return getOrderDate(order).includes(term);
        }
        try { return super.filterOrderBySearch(order, searchDetails); }
        catch (_e) { return true; }
    },

    _searchOrder(order, fieldValue) {
        if (fieldValue?.fieldName === "PRODUCT") {
            const term = (fieldValue.searchTerm || "").toLowerCase().trim();
            if (!term) return true;
            return getOrderProductNames(order).includes(term);
        }
        if (fieldValue?.fieldName === "PAYMENT_METHOD") {
            const term = (fieldValue.searchTerm || "").toLowerCase().trim();
            if (!term) return true;
            return getOrderPaymentMethods(order).includes(term);
        }
        if (fieldValue?.fieldName === "ORDER_DATE") {
            const term = (fieldValue.searchTerm || "").toLowerCase().trim();
            if (!term) return true;
            return getOrderDate(order).includes(term);
        }
        try { return super._searchOrder(order, fieldValue); }
        catch (_e) { return true; }
    },
});