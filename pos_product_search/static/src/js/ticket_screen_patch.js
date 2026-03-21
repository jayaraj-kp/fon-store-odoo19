///** @odoo-module **/
//
//import { patch } from "@web/core/utils/patch";
//import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
//import { _t } from "@web/core/l10n/translation";
//
//function getOrderProductNames(order) {
//    const lines =
//        (typeof order.get_orderlines === "function" && order.get_orderlines()) ||
//        order.lines || order.orderlines || [];
//    return Array.from(lines)
//        .map((line) =>
//            (typeof line.get_full_product_name === "function" && line.get_full_product_name()) ||
//            line.full_product_name || line.product_name ||
//            (line.product_id && (line.product_id.display_name || line.product_id.name)) ||
//            (line.product && (line.product.display_name || line.product.name)) || ""
//        )
//        .filter(Boolean).join(" ").toLowerCase();
//}
//
//patch(TicketScreen.prototype, {
//    /**
//     * _getSearchFields() is what getSearchBarConfig() actually calls.
//     * This populates the SearchBar dropdown in Odoo 19.
//     */
//    _getSearchFields() {
//        let fields = {};
//        try { fields = super._getSearchFields() || {}; } catch (_e) {}
//        return {
//            ...fields,
//            PRODUCT: {
//                displayName: _t("Product"),
//                modelField: "lines.product_id.display_name",
//                repr: (order) => getOrderProductNames(order),
//            },
//        };
//    },
//
//    // Keep getSearchFields patched too as safety net
//    getSearchFields() {
//        let fields = {};
//        try { fields = super.getSearchFields() || {}; } catch (_e) {}
//        return {
//            ...fields,
//            PRODUCT: {
//                displayName: _t("Product"),
//                modelField: "lines.product_id.display_name",
//                repr: (order) => getOrderProductNames(order),
//            },
//        };
//    },
//
//    /**
//     * _doesOrderPassFilter is confirmed present in this instance.
//     * Called with (order, {fieldName, searchTerm}).
//     */
//    _doesOrderPassFilter(order, { fieldName, searchTerm }) {
//        if (fieldName === "PRODUCT") {
//            const term = (searchTerm || "").toLowerCase().trim();
//            if (!term) return true;
//            return getOrderProductNames(order).includes(term);
//        }
//        try { return super._doesOrderPassFilter(order, { fieldName, searchTerm }); }
//        catch (_e) { return true; }
//    },
//
//    filterOrderBySearch(order, searchDetails) {
//        if (searchDetails?.fieldName === "PRODUCT") {
//            const term = (searchDetails.searchTerm || "").toLowerCase().trim();
//            if (!term) return true;
//            return getOrderProductNames(order).includes(term);
//        }
//        try { return super.filterOrderBySearch(order, searchDetails); }
//        catch (_e) { return true; }
//    },
//
//    _searchOrder(order, fieldValue) {
//        if (fieldValue?.fieldName === "PRODUCT") {
//            const term = (fieldValue.searchTerm || "").toLowerCase().trim();
//            if (!term) return true;
//            return getOrderProductNames(order).includes(term);
//        }
//        try { return super._searchOrder(order, fieldValue); }
//        catch (_e) { return true; }
//    },
//});

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
    // Odoo 19 stores payment lines in different ways — try all
    const paymentLines =
        (typeof order.get_paymentlines === "function" && order.get_paymentlines()) ||
        order.payment_ids ||
        order.paymentlines ||
        order.payment_lines ||
        [];
    return Array.from(paymentLines)
        .map((line) =>
            (line.payment_method_id && (line.payment_method_id.name || line.payment_method_id.display_name)) ||
            (line.payment_method && (line.payment_method.name || line.payment_method.display_name)) ||
            line.name || ""
        )
        .filter(Boolean).join(" ").toLowerCase();
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
        try { return super._searchOrder(order, fieldValue); }
        catch (_e) { return true; }
    },
});