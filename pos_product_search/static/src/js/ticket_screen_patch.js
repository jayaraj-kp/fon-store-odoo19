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

// ─── Bill amount (numeric exact match) ───────────────────────────────────────
function getOrderAmountNum(order) {
    const amount =
        order.amount_total ??
        (typeof order.getRoundedGrandTotal === "function" && order.getRoundedGrandTotal()) ??
        0;
    return parseFloat(amount) || 0;
}

function amountMatchesOrder(order, searchTerm) {
    const term = (searchTerm || "").trim();
    if (!term) return true;
    const searchNum = parseFloat(term);
    if (isNaN(searchNum)) return false;
    return Math.abs(getOrderAmountNum(order) - searchNum) < 0.001;
}

// ─── Field definitions ────────────────────────────────────────────────────────
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
            repr: (order) => String(getOrderAmountNum(order)),
        },
    };
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

    /**
     * Override getFilteredOrderList to intercept AMOUNT searches BEFORE
     * fuzzyLookup is called (which causes "900" to match "9800", "980" etc).
     * For all other fields, call super normally.
     */
    getFilteredOrderList() {
        const { fieldName, searchTerm } = this.state.search || {};

        if (fieldName === "AMOUNT" && searchTerm) {
            // Temporarily clear the search so super() returns all orders unfiltered
            const savedSearch = this.state.search;
            this.state.search = { fieldName: "AMOUNT", searchTerm: "" };
            let orders = super.getFilteredOrderList();
            this.state.search = savedSearch;

            // Now apply exact numeric filter ourselves
            return orders.filter((order) => amountMatchesOrder(order, searchTerm));
        }

        return super.getFilteredOrderList();
    },

    _doesOrderPassFilter(order, { fieldName, searchTerm }) {
        if (fieldName === "AMOUNT") return amountMatchesOrder(order, searchTerm);
        try { return super._doesOrderPassFilter(order, { fieldName, searchTerm }); }
        catch (_e) { return true; }
    },

    filterOrderBySearch(order, searchDetails) {
        if (searchDetails?.fieldName === "AMOUNT") {
            return amountMatchesOrder(order, searchDetails.searchTerm);
        }
        try { return super.filterOrderBySearch(order, searchDetails); }
        catch (_e) { return true; }
    },
});