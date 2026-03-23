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
            // repr returns a UNIQUE string per exact amount
            // We pad to 10 decimals so fuzzyLookup only matches exact numeric strings
            // e.g. "900" repr is "900.0000000000" — fuzzy won't match "9800.0000000000"
            repr: (order) => {
                const num = getOrderAmountNum(order);
                // Format: fixed 10 decimal places — makes fuzzy matching effectively exact
                return num.toFixed(10);
            },
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
     * Override onSearch to handle AMOUNT specially.
     * For AMOUNT: pad the searchTerm to 10 decimals so fuzzyLookup
     * matches exactly (repr also uses 10 decimals).
     * e.g. user types "900" → we search "900.0000000000"
     *      repr of ₹900 order = "900.0000000000" → exact match ✓
     *      repr of ₹9800 order = "9800.0000000000" → no match ✓
     */
    async onSearch(search) {
        if (search?.fieldName === "AMOUNT" && search?.searchTerm) {
            const num = parseFloat(search.searchTerm);
            if (!isNaN(num)) {
                // Replace searchTerm with zero-padded version to match repr format
                search = { ...search, searchTerm: num.toFixed(10) };
            }
        }
        return super.onSearch(search);
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