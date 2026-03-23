/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { _t } from "@web/core/l10n/translation";

// ─── Helpers ──────────────────────────────────────────────────────────────────
function getOrderProductNames(order) {
    const lines = order?.getOrderlines?.() || order?.lines || [];
    return Array.from(lines)
        .map((line) =>
            (typeof line.get_full_product_name === "function" && line.get_full_product_name()) ||
            line.full_product_name || line.product_name ||
            (line.product_id && (line.product_id.display_name || line.product_id.name)) ||
            (line.product && (line.product.display_name || line.product.name)) || ""
        ).filter(Boolean).join(" ").toLowerCase();
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
        ).filter(Boolean).join(" ").toLowerCase();
}

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
    } catch (_e) { return String(raw).toLowerCase(); }
}

function getOrderMobile(order) {
    return (
        order.mobile || order.phone ||
        order.partner_id?.mobile || order.partner_id?.phone ||
        (typeof order.getPartner === "function" && order.getPartner()?.mobile) ||
        (typeof order.getPartner === "function" && order.getPartner()?.phone) || ""
    ).toString().toLowerCase();
}

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
        Array.from(product.pos_category_ids || []).forEach((pc) => {
            const name = pc.name || pc.display_name;
            if (name) cats.add(name.toLowerCase());
        });
    });
    return [...cats].join(" ");
}

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

// ─── Custom fields that need exact (non-fuzzy) matching ───────────────────────
const EXACT_FIELDS = new Set(["AMOUNT"]);

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
     * Override getFilteredOrderList ONLY for AMOUNT.
     * Key: do NOT mutate this.state — instead replicate the parent's
     * order-gathering logic and apply our own filter on top.
     */
    getFilteredOrderList() {
        const { fieldName, searchTerm } = this.state.search || {};

        // For non-AMOUNT fields, use the normal path
        if (!EXACT_FIELDS.has(fieldName) || !searchTerm) {
            return super.getFilteredOrderList();
        }

        // ── Replicate parent's order gathering WITHOUT the fuzzyLookup step ──
        const orderModel = this.pos.models["pos.order"];

        // 1. Get base set of orders (same logic as parent)
        let orders = this.state.filter === "SYNCED"
            ? orderModel.filter((o) => o.finalized && o.uiState.displayed)
            : orderModel.filter(this.activeOrderFilter);

        // 2. Apply status filter (same as parent)
        if (this.state.filter && !["ACTIVE_ORDERS", "SYNCED"].includes(this.state.filter)) {
            orders = orders.filter((order) => {
                const screen = order.getScreenData();
                return this._getScreenToStatusMap()[screen.name] === this.state.filter;
            });
        }

        // 3. Apply AMOUNT exact filter (replaces fuzzyLookup)
        orders = orders.filter((order) => amountMatchesOrder(order, searchTerm));

        // 4. Apply partner filter if present (same as parent)
        if (this.state.search.partnerId && fieldName === "PARTNER") {
            orders = orders.filter((order) => order.partner_id?.id === this.state.search.partnerId);
        }

        // 5. Apply preset filter if present (same as parent)
        if (this.state.selectedPreset) {
            orders = orders.filter((order) => order.preset_id?.id === this.state.selectedPreset.id);
        }

        // 6. Sort (same as parent)
        const sortOrders = (orders, ascending = false) =>
            orders.sort((a, b) => {
                const dateA = a.date_order;
                const dateB = b.date_order;
                if (!dateA.equals(dateB)) return ascending ? dateA - dateB : dateB - dateA;
                const nameA = parseInt(a.pos_reference?.replace(/\D/g, "")) || 0;
                const nameB = parseInt(b.pos_reference?.replace(/\D/g, "")) || 0;
                return ascending ? nameA - nameB : nameB - nameA;
            });

        // 7. Paginate (same as parent)
        if (this.state.filter === "SYNCED") {
            return sortOrders(orders).slice(
                (this.state.page - 1) * this.state.nbrByPage,
                this.state.page * this.state.nbrByPage
            );
        } else {
            if (this.pos.screenState?.ticketSCreen) {
                this.pos.screenState.ticketSCreen.totalCount = orders.length;
            }
            return sortOrders(orders, true).slice(
                (this.state.page - 1) * this.state.nbrByPage,
                this.state.page * this.state.nbrByPage
            );
        }
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