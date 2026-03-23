/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { _t } from "@web/core/l10n/translation";

// ─── Product names ────────────────────────────────────────────────────────────
function getOrderProductNames(order) {
    const lines = order?.getOrderlines?.() || order?.lines || [];
    return Array.from(lines)
        .map((line) =>
            (typeof line.get_full_product_name === "function" && line.get_full_product_name()) ||
            line.full_product_name || line.product_name ||
            (line.product_id && (line.product_id.display_name || line.product_id.name)) ||
            (line.product && (line.product.display_name || line.product.name)) || ""
        )
        .filter(Boolean).join(" ").toLowerCase();
}

// ─── Payment methods ──────────────────────────────────────────────────────────
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

// ─── Date ─────────────────────────────────────────────────────────────────────
function getOrderDate(order) {
    const raw = order.date_order || order.creation_date || order.date || "";
    if (!raw) return "";
    try {
        const d = new Date(raw);
        const pad = (n) => String(n).padStart(2, "0");
        const yyyy = d.getFullYear();
        const mm = pad(d.getMonth() + 1);
        const dd = pad(d.getDate());
        return `${yyyy}-${mm}-${dd} ${dd}/${mm}/${yyyy} ${mm}/${dd}/${yyyy} ${raw}`.toLowerCase();
    } catch (_e) {
        return String(raw).toLowerCase();
    }
}

// ─── Customer phone/mobile ────────────────────────────────────────────────────
function getOrderMobile(order) {
    return (
        order.mobile ||
        order.phone ||
        order.partner_id?.mobile ||
        order.partner_id?.phone ||
        (typeof order.getPartner === "function" && order.getPartner()?.mobile) ||
        (typeof order.getPartner === "function" && order.getPartner()?.phone) ||
        ""
    ).toString().toLowerCase();
}

// ─── Product category ─────────────────────────────────────────────────────────
function getOrderCategories(order) {
    const lines = order?.getOrderlines?.() || order?.lines || [];
    const cats = new Set();
    Array.from(lines).forEach((line) => {
        const product = line.product_id || line.product;
        if (!product) return;
        const categ = product.categ_id;
        if (categ) {
            const name = categ.name || categ.display_name || categ.complete_name;
            if (name) cats.add(name.toLowerCase());
        }
        const posCategs = product.pos_category_ids || [];
        Array.from(posCategs).forEach((pc) => {
            const name = pc.name || pc.display_name;
            if (name) cats.add(name.toLowerCase());
        });
    });
    return [...cats].join(" ");
}

// ─── Bill amount ──────────────────────────────────────────────────────────────
// Uses EXACT numeric comparison: "200" matches only ₹200 and ₹200.00
// NOT ₹2000, ₹1200, ₹202 etc.
function getOrderAmountNum(order) {
    const amount =
        order.amount_total ??
        (typeof order.getRoundedGrandTotal === "function" && order.getRoundedGrandTotal()) ??
        (typeof order.get_total_with_tax === "function" && order.get_total_with_tax()) ??
        0;
    return parseFloat(amount) || 0;
}

function matchesAmount(order, searchTerm) {
    const term = (searchTerm || "").trim();
    if (!term) return true;
    const searchNum = parseFloat(term);
    if (isNaN(searchNum)) return false;
    const orderAmount = getOrderAmountNum(order);
    // Exact match: 200 matches 200.00 exactly
    return Math.abs(orderAmount - searchNum) < 0.001;
}

// ─── Shared field definitions ─────────────────────────────────────────────────
function buildSearchFields(existingFields) {
    return {
        ...existingFields,
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
        MOBILE: {
            displayName: _t("Phone / Mobile"),
            modelField: "mobile",
            repr: (order) => getOrderMobile(order),
        },
        CATEGORY: {
            displayName: _t("Product Category"),
            modelField: "lines.product_id.categ_id.name",
            repr: (order) => getOrderCategories(order),
        },
        AMOUNT: {
            displayName: _t("Bill Amount"),
            modelField: "amount_total",
            // repr returns the exact amount string for display in dropdown
            repr: (order) => {
                const num = getOrderAmountNum(order);
                return `${num.toFixed(2)}`;
            },
        },
    };
}

// ─── Filter logic ─────────────────────────────────────────────────────────────
function matchesCustomField(order, fieldName, searchTerm) {
    if (!fieldName) return null;
    const term = (searchTerm || "").trim();

    switch (fieldName) {
        case "PRODUCT":
            if (!term) return true;
            return getOrderProductNames(order).includes(term.toLowerCase());
        case "PAYMENT_METHOD":
            if (!term) return true;
            return getOrderPaymentMethods(order).includes(term.toLowerCase());
        case "ORDER_DATE":
            if (!term) return true;
            return getOrderDate(order).includes(term.toLowerCase());
        case "MOBILE":
            if (!term) return true;
            return getOrderMobile(order).includes(term.toLowerCase());
        case "CATEGORY":
            if (!term) return true;
            return getOrderCategories(order).includes(term.toLowerCase());
        case "AMOUNT":
            return matchesAmount(order, term);
        default:
            return null; // not a custom field — let super handle it
    }
}

patch(TicketScreen.prototype, {
    _getSearchFields() {
        let fields = {};
        try { fields = super._getSearchFields() || {}; } catch (_e) {}
        return buildSearchFields(fields);
    },

    getSearchFields() {
        let fields = {};
        try { fields = super.getSearchFields() || {}; } catch (_e) {}
        return buildSearchFields(fields);
    },

    _doesOrderPassFilter(order, { fieldName, searchTerm }) {
        const result = matchesCustomField(order, fieldName, searchTerm);
        if (result !== null) return result;
        try { return super._doesOrderPassFilter(order, { fieldName, searchTerm }); }
        catch (_e) { return true; }
    },

    filterOrderBySearch(order, searchDetails) {
        const result = matchesCustomField(order, searchDetails?.fieldName, searchDetails?.searchTerm);
        if (result !== null) return result;
        try { return super.filterOrderBySearch(order, searchDetails); }
        catch (_e) { return true; }
    },

    _searchOrder(order, fieldValue) {
        const result = matchesCustomField(order, fieldValue?.fieldName, fieldValue?.searchTerm);
        if (result !== null) return result;
        try { return super._searchOrder(order, fieldValue); }
        catch (_e) { return true; }
    },
});