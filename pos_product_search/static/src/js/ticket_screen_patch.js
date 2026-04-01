/////** @odoo-module **/
////
////import { patch } from "@web/core/utils/patch";
////import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
////import { Component, useState, xml } from "@odoo/owl";
////import { Dialog } from "@web/core/dialog/dialog";
////import { _t } from "@web/core/l10n/translation";
////
////// ═══════════════════════════════════════════════════════════════════════════════
////// CUSTOM FILTER DIALOG — uses Odoo 19 Dialog component directly
////// ═══════════════════════════════════════════════════════════════════════════════
////
////class CustomFilterDialog extends Component {
////    static components = { Dialog };
////    static props = ["close", "confirm"];
////    static template = xml`
////        <Dialog title="'Custom Filter'">
////            <div class="p-3" style="min-width:360px">
////                <div class="mb-3 text-muted small">Match orders where:</div>
////
////                <div class="mb-3">
////                    <label class="form-label fw-bold">Field</label>
////                    <select class="form-select" t-model="state.field"
////                            t-on-change="onFieldChange">
////                        <t t-foreach="fields" t-as="f" t-key="f.key">
////                            <option t-att-value="f.key" t-esc="f.label"/>
////                        </t>
////                    </select>
////                </div>
////
////                <div class="mb-3">
////                    <label class="form-label fw-bold">Condition</label>
////                    <select class="form-select" t-model="state.operator">
////                        <t t-foreach="currentOperators" t-as="op" t-key="op.key">
////                            <option t-att-value="op.key" t-esc="op.label"/>
////                        </t>
////                    </select>
////                </div>
////
////                <div class="mb-4">
////                    <label class="form-label fw-bold">Value</label>
////                    <input class="form-control"
////                           type="text"
////                           t-model="state.value"
////                           placeholder="Enter value..."
////                           t-on-keydown="onKeydown"/>
////                </div>
////
////                <div class="d-flex gap-2 justify-content-end">
////                    <button class="btn btn-secondary" t-on-click="() => props.close()">
////                        Discard
////                    </button>
////                    <button class="btn btn-primary"
////                            t-att-disabled="!state.value"
////                            t-on-click="onApply">
////                        Apply Filter
////                    </button>
////                </div>
////            </div>
////        </Dialog>
////    `;
////
////    setup() {
////        this.fields = [
////            { key: "amount_total",   label: "Bill Amount" },
////            { key: "mobile",         label: "Phone / Mobile" },
////            { key: "partner_name",   label: "Customer Name" },
////            { key: "product_name",   label: "Product Name" },
////            { key: "payment_method", label: "Payment Method" },
////            { key: "date_order",     label: "Date (YYYY-MM-DD)" },
////            { key: "category",       label: "Product Category" },
////        ];
////        this.operatorMap = {
////            amount_total: [
////                { key: "=",  label: "is equal to" },
////                { key: ">=", label: "is greater than or equal" },
////                { key: "<=", label: "is less than or equal" },
////                { key: ">",  label: "is greater than" },
////                { key: "<",  label: "is less than" },
////            ],
////            default: [
////                { key: "ilike", label: "contains" },
////                { key: "=",     label: "is equal to" },
////            ],
////        };
////        this.state = useState({
////            field: "amount_total",
////            operator: "=",
////            value: "",
////        });
////    }
////
////    get currentOperators() {
////        return this.operatorMap[this.state.field] || this.operatorMap.default;
////    }
////
////    onFieldChange() {
////        const ops = this.currentOperators;
////        this.state.operator = ops[0].key;
////    }
////
////    onKeydown(e) {
////        if (e.key === "Enter" && this.state.value) this.onApply();
////    }
////
////    onApply() {
////        if (!this.state.value) return;
////        this.props.confirm({
////            field: this.state.field,
////            operator: this.state.operator,
////            value: this.state.value,
////        });
////        this.props.close();
////    }
////}
////
////// ═══════════════════════════════════════════════════════════════════════════════
////// HELPERS
////// ═══════════════════════════════════════════════════════════════════════════════
////
////function getOrderProductNames(order) {
////    const lines = order?.getOrderlines?.() || order?.lines || [];
////    return Array.from(lines)
////        .map((line) =>
////            (typeof line.get_full_product_name === "function" && line.get_full_product_name()) ||
////            line.full_product_name || line.product_name ||
////            (line.product_id && (line.product_id.display_name || line.product_id.name)) ||
////            (line.product && (line.product.display_name || line.product.name)) || ""
////        ).filter(Boolean).join(" ").toLowerCase();
////}
////
////function getOrderPaymentMethods(order) {
////    const paymentLines =
////        (typeof order.get_paymentlines === "function" && order.get_paymentlines()) ||
////        order.payment_ids || order.paymentlines || order.payment_lines || [];
////    return Array.from(paymentLines)
////        .map((line) =>
////            (line.payment_method_id && (line.payment_method_id.name || line.payment_method_id.display_name)) ||
////            (line.payment_method && (line.payment_method.name || line.payment_method.display_name)) ||
////            line.name || ""
////        ).filter(Boolean).join(" ").toLowerCase();
////}
////
////function getOrderDate(order) {
////    const raw = order.date_order || order.creation_date || order.date || "";
////    if (!raw) return "";
////    try {
////        const d = new Date(raw);
////        const pad = (n) => String(n).padStart(2, "0");
////        const yyyy = d.getFullYear();
////        const mm = pad(d.getMonth() + 1);
////        const dd = pad(d.getDate());
////        return `${yyyy}-${mm}-${dd} ${dd}/${mm}/${yyyy} ${mm}/${dd}/${yyyy} ${raw}`.toLowerCase();
////    } catch (_e) { return String(raw).toLowerCase(); }
////}
////
////function getOrderMobile(order) {
////    return (
////        order.mobile || order.phone ||
////        order.partner_id?.mobile || order.partner_id?.phone ||
////        (typeof order.getPartner === "function" && order.getPartner()?.mobile) ||
////        (typeof order.getPartner === "function" && order.getPartner()?.phone) || ""
////    ).toString().toLowerCase();
////}
////
////function getOrderCategories(order) {
////    const lines = order?.getOrderlines?.() || order?.lines || [];
////    const cats = new Set();
////    Array.from(lines).forEach((line) => {
////        const product = line.product_id || line.product;
////        if (!product) return;
////        const categ = product.categ_id;
////        if (categ) {
////            const name = categ.name || categ.display_name || categ.complete_name;
////            if (name) cats.add(name.toLowerCase());
////        }
////        Array.from(product.pos_category_ids || []).forEach((pc) => {
////            const name = pc.name || pc.display_name;
////            if (name) cats.add(name.toLowerCase());
////        });
////    });
////    return [...cats].join(" ");
////}
////
////function getOrderAmountNum(order) {
////    const amount =
////        order.amount_total ??
////        (typeof order.getRoundedGrandTotal === "function" && order.getRoundedGrandTotal()) ?? 0;
////    return parseFloat(amount) || 0;
////}
////
////function amountMatchesOrder(order, searchTerm) {
////    const term = (searchTerm || "").trim();
////    if (!term) return true;
////    const searchNum = parseFloat(term);
////    if (isNaN(searchNum)) return false;
////    return Math.abs(getOrderAmountNum(order) - searchNum) < 0.001;
////}
////
////function matchesCustomFilter(order, filter) {
////    if (!filter || !filter.value) return true;
////    const { field, operator, value } = filter;
////    const val = value.toString().toLowerCase().trim();
////
////    if (field === "amount_total") {
////        const orderNum = getOrderAmountNum(order);
////        const searchNum = parseFloat(value);
////        if (isNaN(searchNum)) return false;
////        if (operator === "=")  return Math.abs(orderNum - searchNum) < 0.001;
////        if (operator === ">=") return orderNum >= searchNum;
////        if (operator === "<=") return orderNum <= searchNum;
////        if (operator === ">")  return orderNum > searchNum;
////        if (operator === "<")  return orderNum < searchNum;
////    }
////    if (field === "mobile")
////        return operator === "ilike" ? getOrderMobile(order).includes(val) : getOrderMobile(order) === val;
////    if (field === "partner_name") {
////        const name = ((typeof order.getPartnerName === "function" && order.getPartnerName()) || order.partner_id?.name || "").toLowerCase();
////        return operator === "ilike" ? name.includes(val) : name === val;
////    }
////    if (field === "product_name")
////        return operator === "ilike" ? getOrderProductNames(order).includes(val) : getOrderProductNames(order) === val;
////    if (field === "payment_method")
////        return operator === "ilike" ? getOrderPaymentMethods(order).includes(val) : getOrderPaymentMethods(order) === val;
////    if (field === "date_order")
////        return getOrderDate(order).includes(val);
////    if (field === "category")
////        return operator === "ilike" ? getOrderCategories(order).includes(val) : getOrderCategories(order) === val;
////    return true;
////}
////
////function buildSearchFields(existingFields) {
////    return {
////        ...existingFields,
////        PRODUCT: { displayName: _t("Product"), modelField: "lines.product_id.display_name", repr: (order) => getOrderProductNames(order) },
////        PAYMENT_METHOD: { displayName: _t("Payment Method"), modelField: "payment_ids.payment_method_id.name", repr: (order) => getOrderPaymentMethods(order) },
////        ORDER_DATE: { displayName: _t("Date"), modelField: "date_order", repr: (order) => getOrderDate(order) },
////        MOBILE: { displayName: _t("Phone / Mobile"), modelField: "mobile", repr: (order) => getOrderMobile(order) },
////        CATEGORY: { displayName: _t("Product Category"), modelField: "lines.product_id.categ_id.name", repr: (order) => getOrderCategories(order) },
////        AMOUNT: { displayName: _t("Bill Amount"), modelField: "amount_total", repr: (order) => String(getOrderAmountNum(order)) },
////        CUSTOM_FILTER: { displayName: _t("Custom Filter..."), modelField: "", repr: () => "" },
////    };
////}
////
////const EXACT_FIELDS = new Set(["AMOUNT"]);
////
////function sortOrders(orders, ascending = false) {
////    return orders.sort((a, b) => {
////        const dateA = a.date_order;
////        const dateB = b.date_order;
////        if (!dateA.equals(dateB)) return ascending ? dateA - dateB : dateB - dateA;
////        const nameA = parseInt(a.pos_reference?.replace(/\D/g, "")) || 0;
////        const nameB = parseInt(b.pos_reference?.replace(/\D/g, "")) || 0;
////        return ascending ? nameA - nameB : nameB - nameA;
////    });
////}
////
////// ═══════════════════════════════════════════════════════════════════════════════
////// PATCH
////// ═══════════════════════════════════════════════════════════════════════════════
////
////patch(TicketScreen.prototype, {
////    setup() {
////        super.setup(...arguments);
////        this._customFilter = null;
////    },
////
////    _getSearchFields() {
////        let fields = {};
////        try { fields = super._getSearchFields() || {}; } catch (_e) {}
////        return buildSearchFields(fields);
////    },
////
////    getSearchFields() {
////        let fields = {};
////        try { fields = super.getSearchFields() || {}; } catch (_e) {}
////        return buildSearchFields(fields);
////    },
////
////    // Intercept onSearch to open dialog when CUSTOM_FILTER is selected
////    async onSearch(search) {
////        if (search?.fieldName === "CUSTOM_FILTER") {
////            const result = await new Promise((resolve) => {
////                this.dialog.add(CustomFilterDialog, {
////                    confirm: (payload) => resolve(payload),
////                }, {
////                    onClose: () => resolve(null),
////                });
////            });
////            if (result && result.value !== "") {
////                this._customFilter = result;
////                this.state.filter = "CUSTOM_FILTER";
////                this.pos.screenState.ticketSCreen.totalCount = 0;
////                this.pos.screenState.ticketSCreen.offsetByDomain = {};
////                // Clear search so dropdown closes
////                this.state.search = { fieldName: "CUSTOM_FILTER", searchTerm: "" };
////            }
////            return;
////        }
////        return super.onSearch(search);
////    },
////
////    _getFilterOptions() {
////        let options;
////        try { options = super._getFilterOptions(); } catch (_e) { options = new Map(); }
////        if (!options) options = new Map();
////        return options;
////    },
////
////    async onFilterSelected(selectedFilter) {
////        this._customFilter = null;
////        return super.onFilterSelected(selectedFilter);
////    },
////
////    getFilteredOrderList() {
////        const { fieldName, searchTerm } = this.state.search || {};
////
////        if (EXACT_FIELDS.has(fieldName) && searchTerm) {
////            const orderModel = this.pos.models["pos.order"];
////            let orders = this.state.filter === "SYNCED"
////                ? orderModel.filter((o) => o.finalized && o.uiState.displayed)
////                : orderModel.filter(this.activeOrderFilter);
////            if (this.state.filter && !["ACTIVE_ORDERS", "SYNCED", "CUSTOM_FILTER"].includes(this.state.filter)) {
////                orders = orders.filter((order) => {
////                    const screen = order.getScreenData();
////                    return this._getScreenToStatusMap()[screen.name] === this.state.filter;
////                });
////            }
////            orders = orders.filter((order) => amountMatchesOrder(order, searchTerm));
////            if (this.state.selectedPreset)
////                orders = orders.filter((order) => order.preset_id?.id === this.state.selectedPreset.id);
////            if (this.state.filter === "SYNCED")
////                return sortOrders(orders).slice((this.state.page - 1) * this.state.nbrByPage, this.state.page * this.state.nbrByPage);
////            if (this.pos.screenState?.ticketSCreen)
////                this.pos.screenState.ticketSCreen.totalCount = orders.length;
////            return sortOrders(orders, true).slice((this.state.page - 1) * this.state.nbrByPage, this.state.page * this.state.nbrByPage);
////        }
////
////        if (this.state.filter === "CUSTOM_FILTER" && this._customFilter) {
////            const orderModel = this.pos.models["pos.order"];
////            let orders = orderModel.filter(this.activeOrderFilter);
////            orders = orders.filter((order) => matchesCustomFilter(order, this._customFilter));
////            if (this.state.selectedPreset)
////                orders = orders.filter((order) => order.preset_id?.id === this.state.selectedPreset.id);
////            if (this.pos.screenState?.ticketSCreen)
////                this.pos.screenState.ticketSCreen.totalCount = orders.length;
////            return sortOrders(orders, true).slice((this.state.page - 1) * this.state.nbrByPage, this.state.page * this.state.nbrByPage);
////        }
////
////        return super.getFilteredOrderList();
////    },
////
////    _doesOrderPassFilter(order, { fieldName, searchTerm }) {
////        if (fieldName === "AMOUNT") return amountMatchesOrder(order, searchTerm);
////        try { return super._doesOrderPassFilter(order, { fieldName, searchTerm }); }
////        catch (_e) { return true; }
////    },
////
////    filterOrderBySearch(order, searchDetails) {
////        if (searchDetails?.fieldName === "AMOUNT") return amountMatchesOrder(order, searchDetails.searchTerm);
////        try { return super.filterOrderBySearch(order, searchDetails); }
////        catch (_e) { return true; }
////    },
////});
///** @odoo-module **/
///** @odoo-module **/
//
//import { patch } from "@web/core/utils/patch";
//import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
//import { Component, useState, xml } from "@odoo/owl";
//import { Dialog } from "@web/core/dialog/dialog";
//import { _t } from "@web/core/l10n/translation";
//
//// ═══════════════════════════════════════════════════════════════════════════════
//// CUSTOM FILTER DIALOG — uses Odoo 19 Dialog component directly
//// ═══════════════════════════════════════════════════════════════════════════════
//
//class CustomFilterDialog extends Component {
//    static components = { Dialog };
//    static props = ["close", "confirm"];
//    static template = xml`
//        <Dialog title="'Custom Filter'">
//            <div class="p-3" style="min-width:360px">
//                <div class="mb-3 text-muted small">Match orders where:</div>
//
//                <div class="mb-3">
//                    <label class="form-label fw-bold">Field</label>
//                    <select class="form-select" t-model="state.field"
//                            t-on-change="onFieldChange">
//                        <t t-foreach="fields" t-as="f" t-key="f.key">
//                            <option t-att-value="f.key" t-esc="f.label"/>
//                        </t>
//                    </select>
//                </div>
//
//                <div class="mb-3">
//                    <label class="form-label fw-bold">Condition</label>
//                    <select class="form-select" t-model="state.operator">
//                        <t t-foreach="currentOperators" t-as="op" t-key="op.key">
//                            <option t-att-value="op.key" t-esc="op.label"/>
//                        </t>
//                    </select>
//                </div>
//
//                <div class="mb-4">
//                    <label class="form-label fw-bold">Value</label>
//                    <input class="form-control"
//                           type="text"
//                           t-model="state.value"
//                           placeholder="Enter value..."
//                           t-on-keydown="onKeydown"/>
//                </div>
//
//                <div class="d-flex gap-2 justify-content-end">
//                    <button class="btn btn-secondary" t-on-click="() => props.close()">
//                        Discard
//                    </button>
//                    <button class="btn btn-primary"
//                            t-att-disabled="!state.value"
//                            t-on-click="onApply">
//                        Apply Filter
//                    </button>
//                </div>
//            </div>
//        </Dialog>
//    `;
//
//    setup() {
//        this.fields = [
//            { key: "amount_total",   label: "Bill Amount" },
//            { key: "mobile",         label: "Phone / Mobile" },
//            { key: "partner_name",   label: "Customer Name" },
//            { key: "product_name",   label: "Product Name" },
//            { key: "payment_method", label: "Payment Method" },
//            { key: "date_order",     label: "Date (YYYY-MM-DD)" },
//            { key: "category",       label: "Product Category" },
//        ];
//        this.operatorMap = {
//            amount_total: [
//                { key: "=",  label: "is equal to" },
//                { key: ">=", label: "is greater than or equal" },
//                { key: "<=", label: "is less than or equal" },
//                { key: ">",  label: "is greater than" },
//                { key: "<",  label: "is less than" },
//            ],
//            default: [
//                { key: "ilike", label: "contains" },
//                { key: "=",     label: "is equal to" },
//            ],
//        };
//        this.state = useState({
//            field: "amount_total",
//            operator: "=",
//            value: "",
//        });
//    }
//
//    get currentOperators() {
//        return this.operatorMap[this.state.field] || this.operatorMap.default;
//    }
//
//    onFieldChange() {
//        const ops = this.currentOperators;
//        this.state.operator = ops[0].key;
//    }
//
//    onKeydown(e) {
//        if (e.key === "Enter" && this.state.value) this.onApply();
//    }
//
//    onApply() {
//        if (!this.state.value) return;
//        this.props.confirm({
//            field: this.state.field,
//            operator: this.state.operator,
//            value: this.state.value,
//        });
//        this.props.close();
//    }
//}
//
//// ═══════════════════════════════════════════════════════════════════════════════
//// HELPERS
//// ═══════════════════════════════════════════════════════════════════════════════
//
//function getOrderProductNames(order) {
//    const lines = order?.getOrderlines?.() || order?.lines || [];
//    return Array.from(lines)
//        .map((line) =>
//            (typeof line.get_full_product_name === "function" && line.get_full_product_name()) ||
//            line.full_product_name || line.product_name ||
//            (line.product_id && (line.product_id.display_name || line.product_id.name)) ||
//            (line.product && (line.product.display_name || line.product.name)) || ""
//        ).filter(Boolean).join(" ").toLowerCase();
//}
//
//function getOrderPaymentMethods(order) {
//    const paymentLines =
//        (typeof order.get_paymentlines === "function" && order.get_paymentlines()) ||
//        order.payment_ids || order.paymentlines || order.payment_lines || [];
//    return Array.from(paymentLines)
//        .map((line) =>
//            (line.payment_method_id && (line.payment_method_id.name || line.payment_method_id.display_name)) ||
//            (line.payment_method && (line.payment_method.name || line.payment_method.display_name)) ||
//            line.name || ""
//        ).filter(Boolean).join(" ").toLowerCase();
//}
//
//function getOrderDate(order) {
//    const raw = order.date_order || order.creation_date || order.date || "";
//    if (!raw) return "";
//    try {
//        const d = new Date(raw);
//        const pad = (n) => String(n).padStart(2, "0");
//        const yyyy = d.getFullYear();
//        const mm = pad(d.getMonth() + 1);
//        const dd = pad(d.getDate());
//        return `${yyyy}-${mm}-${dd} ${dd}/${mm}/${yyyy} ${mm}/${dd}/${yyyy} ${raw}`.toLowerCase();
//    } catch (_e) { return String(raw).toLowerCase(); }
//}
//
//function getOrderMobile(order) {
//    return (
//        order.mobile || order.phone ||
//        order.partner_id?.mobile || order.partner_id?.phone ||
//        (typeof order.getPartner === "function" && order.getPartner()?.mobile) ||
//        (typeof order.getPartner === "function" && order.getPartner()?.phone) || ""
//    ).toString().toLowerCase();
//}
//
//function getOrderCategories(order) {
//    const lines = order?.getOrderlines?.() || order?.lines || [];
//    const cats = new Set();
//    Array.from(lines).forEach((line) => {
//        const product = line.product_id || line.product;
//        if (!product) return;
//        const categ = product.categ_id;
//        if (categ) {
//            const name = categ.name || categ.display_name || categ.complete_name;
//            if (name) cats.add(name.toLowerCase());
//        }
//        Array.from(product.pos_category_ids || []).forEach((pc) => {
//            const name = pc.name || pc.display_name;
//            if (name) cats.add(name.toLowerCase());
//        });
//    });
//    return [...cats].join(" ");
//}
//
//function getOrderAmountNum(order) {
//    const amount =
//        order.amount_total ??
//        (typeof order.getRoundedGrandTotal === "function" && order.getRoundedGrandTotal()) ?? 0;
//    return parseFloat(amount) || 0;
//}
//
//function amountMatchesOrder(order, searchTerm) {
//    const term = (searchTerm || "").trim();
//    if (!term) return true;
//    const searchNum = parseFloat(term);
//    if (isNaN(searchNum)) return false;
//    return Math.abs(getOrderAmountNum(order) - searchNum) < 0.001;
//}
//
//function matchesCustomFilter(order, filter) {
//    if (!filter || !filter.value) return true;
//    const { field, operator, value } = filter;
//    const val = value.toString().toLowerCase().trim();
//
//    if (field === "amount_total") {
//        const orderNum = getOrderAmountNum(order);
//        const searchNum = parseFloat(value);
//        if (isNaN(searchNum)) return false;
//        if (operator === "=")  return Math.abs(orderNum - searchNum) < 0.001;
//        if (operator === ">=") return orderNum >= searchNum;
//        if (operator === "<=") return orderNum <= searchNum;
//        if (operator === ">")  return orderNum > searchNum;
//        if (operator === "<")  return orderNum < searchNum;
//    }
//    if (field === "mobile")
//        return operator === "ilike" ? getOrderMobile(order).includes(val) : getOrderMobile(order) === val;
//    if (field === "partner_name") {
//        const name = ((typeof order.getPartnerName === "function" && order.getPartnerName()) || order.partner_id?.name || "").toLowerCase();
//        return operator === "ilike" ? name.includes(val) : name === val;
//    }
//    if (field === "product_name")
//        return operator === "ilike" ? getOrderProductNames(order).includes(val) : getOrderProductNames(order) === val;
//    if (field === "payment_method")
//        return operator === "ilike" ? getOrderPaymentMethods(order).includes(val) : getOrderPaymentMethods(order) === val;
//    if (field === "date_order")
//        return getOrderDate(order).includes(val);
//    if (field === "category")
//        return operator === "ilike" ? getOrderCategories(order).includes(val) : getOrderCategories(order) === val;
//    return true;
//}
//
//function buildSearchFields(existingFields) {
//    return {
//        ...existingFields,
//        PRODUCT: { displayName: _t("Product"), modelField: "lines.product_id.display_name", repr: (order) => getOrderProductNames(order) },
//        PAYMENT_METHOD: { displayName: _t("Payment Method"), modelField: "payment_ids.payment_method_id.name", repr: (order) => getOrderPaymentMethods(order) },
//        ORDER_DATE: { displayName: _t("Date"), modelField: "date_order", repr: (order) => getOrderDate(order) },
//        MOBILE: { displayName: _t("Phone / Mobile"), modelField: "mobile", repr: (order) => getOrderMobile(order) },
//        CATEGORY: { displayName: _t("Product Category"), modelField: "lines.product_id.categ_id.name", repr: (order) => getOrderCategories(order) },
//        AMOUNT: { displayName: _t("Bill Amount"), modelField: "amount_total", repr: (order) => String(getOrderAmountNum(order)) },
//        CUSTOM_FILTER: { displayName: _t("Custom Filter..."), modelField: "", repr: () => "" },
//    };
//}
//
//const EXACT_FIELDS = new Set(["AMOUNT"]);
//
//function sortOrders(orders, ascending = false) {
//    return orders.sort((a, b) => {
//        const dateA = a.date_order ? new Date(a.date_order) : new Date(0);
//        const dateB = b.date_order ? new Date(b.date_order) : new Date(0);
//        if (dateA.getTime() !== dateB.getTime()) return ascending ? dateA - dateB : dateB - dateA;
//        const nameA = parseInt(a.pos_reference?.replace(/\D/g, "")) || 0;
//        const nameB = parseInt(b.pos_reference?.replace(/\D/g, "")) || 0;
//        return ascending ? nameA - nameB : nameB - nameA;
//    });
//}
//
//// ═══════════════════════════════════════════════════════════════════════════════
//// PATCH
//// ═══════════════════════════════════════════════════════════════════════════════
//
//patch(TicketScreen.prototype, {
//    setup() {
//        super.setup(...arguments);
//        this._customFilter = null;
//    },
//
//    _getSearchFields() {
//        let fields = {};
//        try { fields = super._getSearchFields() || {}; } catch (_e) {}
//        return buildSearchFields(fields);
//    },
//
//    getSearchFields() {
//        let fields = {};
//        try { fields = super.getSearchFields() || {}; } catch (_e) {}
//        return buildSearchFields(fields);
//    },
//
//    // Intercept onSearch to open dialog when CUSTOM_FILTER is selected
//    async onSearch(search) {
//        if (search?.fieldName === "CUSTOM_FILTER") {
//            const result = await new Promise((resolve) => {
//                this.dialog.add(CustomFilterDialog, {
//                    confirm: (payload) => resolve(payload),
//                }, {
//                    onClose: () => resolve(null),
//                });
//            });
//            if (result && result.value !== "") {
//                this._customFilter = result;
//                this.state.filter = "CUSTOM_FILTER";
//                // Fix typo ticketSCreen -> ticketScreen, guard with optional chaining
//                if (this.pos.screenState?.ticketScreen) {
//                    this.pos.screenState.ticketScreen.totalCount = 0;
//                    this.pos.screenState.ticketScreen.offsetByDomain = {};
//                }
//                // *** CRITICAL FIX ***
//                // DO NOT reassign this.state.search — SearchBar owns its own
//                // reactive state object. Replacing it from outside destroys the
//                // reactive reference and causes:
//                //   TypeError: Cannot read properties of undefined (reading 'text')
//                //
//                // Instead: call super.onSearch() with the first real search field
//                // (e.g. RECEIPT_NUMBER) and an empty term. This lets SearchBar
//                // reset itself cleanly through its own normal code path.
//                const fields = this.getSearchFields ? this.getSearchFields() : (this._getSearchFields ? this._getSearchFields() : {});
//                // Pick the first non-custom field as the safe reset target
//                const safeField = Object.keys(fields).find((k) => k !== "CUSTOM_FILTER") || "RECEIPT_NUMBER";
//                await super.onSearch({ fieldName: safeField, searchTerm: "" });
//            }
//            return;
//        }
//        return super.onSearch(search);
//    },
//
//    _getFilterOptions() {
//        let options;
//        try { options = super._getFilterOptions(); } catch (_e) { options = new Map(); }
//        if (!options) options = new Map();
//        return options;
//    },
//
//    async onFilterSelected(selectedFilter) {
//        this._customFilter = null;
//        return super.onFilterSelected(selectedFilter);
//    },
//
//    getFilteredOrderList() {
//        const { fieldName, searchTerm } = this.state.search || {};
//
//        if (EXACT_FIELDS.has(fieldName) && searchTerm) {
//            const orderModel = this.pos.models["pos.order"];
//            let orders = this.state.filter === "SYNCED"
//                ? orderModel.filter((o) => o.finalized && o.uiState.displayed)
//                : orderModel.filter(this.activeOrderFilter);
//            if (this.state.filter && !["ACTIVE_ORDERS", "SYNCED", "CUSTOM_FILTER"].includes(this.state.filter)) {
//                orders = orders.filter((order) => {
//                    const screen = order.getScreenData();
//                    return this._getScreenToStatusMap()[screen.name] === this.state.filter;
//                });
//            }
//            orders = orders.filter((order) => amountMatchesOrder(order, searchTerm));
//            if (this.state.selectedPreset)
//                orders = orders.filter((order) => order.preset_id?.id === this.state.selectedPreset.id);
//            if (this.state.filter === "SYNCED")
//                return sortOrders(orders).slice((this.state.page - 1) * this.state.nbrByPage, this.state.page * this.state.nbrByPage);
//            if (this.pos.screenState?.ticketSCreen)
//                this.pos.screenState.ticketSCreen.totalCount = orders.length;
//            return sortOrders(orders, true).slice((this.state.page - 1) * this.state.nbrByPage, this.state.page * this.state.nbrByPage);
//        }
//
//        if (this.state.filter === "CUSTOM_FILTER" && this._customFilter) {
//            const orderModel = this.pos.models["pos.order"];
//            let orders = orderModel.filter(this.activeOrderFilter);
//            orders = orders.filter((order) => matchesCustomFilter(order, this._customFilter));
//            if (this.state.selectedPreset)
//                orders = orders.filter((order) => order.preset_id?.id === this.state.selectedPreset.id);
//            if (this.pos.screenState?.ticketSCreen)
//                this.pos.screenState.ticketSCreen.totalCount = orders.length;
//            return sortOrders(orders, true).slice((this.state.page - 1) * this.state.nbrByPage, this.state.page * this.state.nbrByPage);
//        }
//
//        return super.getFilteredOrderList();
//    },
//
//    _doesOrderPassFilter(order, { fieldName, searchTerm }) {
//        if (fieldName === "AMOUNT") return amountMatchesOrder(order, searchTerm);
//        try { return super._doesOrderPassFilter(order, { fieldName, searchTerm }); }
//        catch (_e) { return true; }
//    },
//
//    filterOrderBySearch(order, searchDetails) {
//        if (searchDetails?.fieldName === "AMOUNT") return amountMatchesOrder(order, searchDetails.searchTerm);
//        try { return super.filterOrderBySearch(order, searchDetails); }
//        catch (_e) { return true; }
//    },
//});
/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { Component, useState, xml } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

// ═══════════════════════════════════════════════════════════════════════════════
// FIELD DEFINITIONS
// ═══════════════════════════════════════════════════════════════════════════════

const FIELD_DEFS = [
    { key: "amount_total",   label: "Bill Amount",       type: "number" },
    { key: "partner_name",   label: "Customer Name",     type: "text"   },
    { key: "mobile",         label: "Phone / Mobile",    type: "text"   },
    { key: "product_name",   label: "Product Name",      type: "text"   },
    { key: "payment_method", label: "Payment Method",    type: "text"   },
    { key: "date_order",     label: "Date (YYYY-MM-DD)", type: "text"   },
    { key: "category",       label: "Product Category",  type: "text"   },
    { key: "pos_reference",  label: "Order Reference",   type: "text"   },
];

const OPERATORS_TEXT = [
    { key: "ilike",     label: "contains"          },
    { key: "not ilike", label: "does not contain"   },
    { key: "=",         label: "is equal to"        },
    { key: "!=",        label: "is not equal to"    },
];

const OPERATORS_NUMBER = [
    { key: "=",  label: "is equal to"                   },
    { key: "!=", label: "is not equal to"                },
    { key: ">",  label: "is greater than"                },
    { key: ">=", label: "is greater than or equal to"    },
    { key: "<",  label: "is less than"                   },
    { key: "<=", label: "is less than or equal to"       },
];

function getOperatorsForField(fieldKey) {
    const def = FIELD_DEFS.find((f) => f.key === fieldKey);
    return def && def.type === "number" ? OPERATORS_NUMBER : OPERATORS_TEXT;
}

function makeRule() {
    return { id: Date.now() + Math.random(), field: "amount_total", operator: "=", value: "" };
}

// ═══════════════════════════════════════════════════════════════════════════════
// NATIVE-STYLE CUSTOM FILTER DIALOG
// ═══════════════════════════════════════════════════════════════════════════════

class NativeCustomFilterDialog extends Component {
    static components = { Dialog };
    static props = ["close", "confirm"];

    static template = xml`
<Dialog title="'Custom Filter'">
  <div style="min-width:580px;">

    <!-- Header: Match any/all + Include archived -->
    <div class="d-flex align-items-center justify-content-between mb-3">
      <div class="d-flex align-items-center gap-2 flex-wrap">
        <span>Match</span>
        <select class="form-select form-select-sm d-inline-block"
                style="width:auto"
                t-model="state.matchMode">
          <option value="any">any</option>
          <option value="all">all</option>
        </select>
        <span>of the following rules:</span>
      </div>
      <div class="form-check form-check-inline m-0">
        <input class="form-check-input" type="checkbox"
               id="cfIncludeArchived"
               t-model="state.includeArchived"/>
        <label class="form-check-label" for="cfIncludeArchived">
          Include archived
        </label>
      </div>
    </div>

    <!-- Rule rows -->
    <div class="d-flex flex-column gap-2 mb-2">
      <t t-foreach="state.rules" t-as="rule" t-key="rule.id">
        <div class="d-flex align-items-center gap-2">

          <!-- Field -->
          <select class="form-select form-select-sm"
                  style="min-width:160px; flex:1"
                  t-att-value="rule.field"
                  t-on-change="(ev) => this.onFieldChange(rule, ev)">
            <t t-foreach="fieldDefs" t-as="fd" t-key="fd.key">
              <option t-att-value="fd.key"
                      t-att-selected="fd.key === rule.field"
                      t-esc="fd.label"/>
            </t>
          </select>

          <!-- Operator -->
          <select class="form-select form-select-sm"
                  style="min-width:180px; flex:1"
                  t-att-value="rule.operator"
                  t-on-change="(ev) => this.onOperatorChange(rule, ev)">
            <t t-foreach="getOperators(rule.field)" t-as="op" t-key="op.key">
              <option t-att-value="op.key"
                      t-att-selected="op.key === rule.operator"
                      t-esc="op.label"/>
            </t>
          </select>

          <!-- Value -->
          <input class="form-control form-control-sm"
                 style="min-width:120px; flex:1"
                 type="text"
                 t-att-value="rule.value"
                 t-on-input="(ev) => this.onValueInput(rule, ev)"
                 t-on-keydown="(ev) => this.onKeydown(ev)"
                 placeholder="Value"/>

          <!-- Delete rule -->
          <button class="btn btn-sm btn-light border"
                  t-att-disabled="state.rules.length === 1 ? true : undefined"
                  t-on-click="() => this.removeRule(rule)"
                  title="Remove rule">
            <i class="fa fa-trash-o"/>
          </button>

        </div>
      </t>
    </div>

    <!-- New Rule link -->
    <div class="mb-3">
      <a href="#" class="text-decoration-none small" t-on-click.prevent="addRule">
        <i class="fa fa-plus me-1"/>New Rule
      </a>
    </div>

    <!-- Action buttons -->
    <div class="d-flex gap-2">
      <button class="btn btn-primary btn-sm"
              t-att-disabled="!canSearch ? true : undefined"
              t-on-click="onSearch">
        Search
      </button>
      <button class="btn btn-secondary btn-sm"
              t-on-click="() => props.close()">
        Discard
      </button>
    </div>

  </div>
</Dialog>
    `;

    setup() {
        this.fieldDefs = FIELD_DEFS;
        this.state = useState({
            matchMode: "any",
            includeArchived: false,
            rules: [makeRule()],
        });
    }

    getOperators(fieldKey) {
        return getOperatorsForField(fieldKey);
    }

    onFieldChange(rule, ev) {
        rule.field = ev.target.value;
        rule.operator = getOperatorsForField(rule.field)[0].key;
    }

    onOperatorChange(rule, ev) {
        rule.operator = ev.target.value;
    }

    onValueInput(rule, ev) {
        rule.value = ev.target.value;
    }

    addRule() {
        this.state.rules.push(makeRule());
    }

    removeRule(rule) {
        if (this.state.rules.length <= 1) return;
        const idx = this.state.rules.findIndex((r) => r.id === rule.id);
        if (idx !== -1) this.state.rules.splice(idx, 1);
    }

    get canSearch() {
        return this.state.rules.some((r) => r.value.trim() !== "");
    }

    onKeydown(ev) {
        if (ev.key === "Enter" && this.canSearch) this.onSearch();
    }

    onSearch() {
        if (!this.canSearch) return;
        this.props.confirm({
            matchMode: this.state.matchMode,
            includeArchived: this.state.includeArchived,
            rules: this.state.rules
                .filter((r) => r.value.trim() !== "")
                .map((r) => ({ field: r.field, operator: r.operator, value: r.value.trim() })),
        });
        this.props.close();
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════════════════════════════

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
        (typeof order.getRoundedGrandTotal === "function" && order.getRoundedGrandTotal()) ?? 0;
    return parseFloat(amount) || 0;
}

function amountMatchesOrder(order, searchTerm) {
    const term = (searchTerm || "").trim();
    if (!term) return true;
    const searchNum = parseFloat(term);
    if (isNaN(searchNum)) return false;
    return Math.abs(getOrderAmountNum(order) - searchNum) < 0.001;
}

function getFieldValue(order, fieldKey) {
    switch (fieldKey) {
        case "amount_total":   return getOrderAmountNum(order);
        case "partner_name":   return ((typeof order.getPartnerName === "function" && order.getPartnerName()) || order.partner_id?.name || "").toLowerCase();
        case "mobile":         return getOrderMobile(order);
        case "product_name":   return getOrderProductNames(order);
        case "payment_method": return getOrderPaymentMethods(order);
        case "date_order":     return getOrderDate(order);
        case "category":       return getOrderCategories(order);
        case "pos_reference":  return (order.pos_reference || order.name || "").toLowerCase();
        default:               return "";
    }
}

function applyOperator(orderVal, operator, rawValue) {
    const isNum = typeof orderVal === "number";
    const val   = isNum ? parseFloat(rawValue) : rawValue.toLowerCase().trim();
    if (isNum && isNaN(val)) return false;
    switch (operator) {
        case "=":         return isNum ? Math.abs(orderVal - val) < 0.001 : orderVal === val;
        case "!=":        return isNum ? Math.abs(orderVal - val) >= 0.001 : orderVal !== val;
        case ">":         return orderVal > val;
        case ">=":        return orderVal >= val;
        case "<":         return orderVal < val;
        case "<=":        return orderVal <= val;
        case "ilike":     return String(orderVal).includes(String(val));
        case "not ilike": return !String(orderVal).includes(String(val));
        default:          return true;
    }
}

function matchesNativeFilter(order, payload) {
    if (!payload || !payload.rules || payload.rules.length === 0) return true;
    const results = payload.rules.map((rule) =>
        applyOperator(getFieldValue(order, rule.field), rule.operator, rule.value)
    );
    return payload.matchMode === "all" ? results.every(Boolean) : results.some(Boolean);
}

// ═══════════════════════════════════════════════════════════════════════════════
// BUILD SEARCH FIELDS
//
// *** THE FIX ***
// Odoo 19's SearchBar template reads field.text (NOT field.displayName).
// Every custom field MUST have a `text` property or the SearchBar crashes with:
//   TypeError: Cannot read properties of undefined (reading 'text')
//
// We set BOTH `text` and `displayName` for maximum compatibility.
// ═══════════════════════════════════════════════════════════════════════════════

function makeField(label, modelField, reprFn) {
    const translatedLabel = _t(label);
    return {
        text: translatedLabel,          // ← required by Odoo 19 SearchBar template
        displayName: translatedLabel,   // ← used by some older Odoo 18/17 code
        modelField,
        repr: reprFn,
    };
}

function buildSearchFields(existingFields) {
    return {
        ...existingFields,
        PRODUCT:        makeField("Product",           "lines.product_id.display_name",      (order) => getOrderProductNames(order)    ),
        PAYMENT_METHOD: makeField("Payment Method",    "payment_ids.payment_method_id.name", (order) => getOrderPaymentMethods(order)  ),
        ORDER_DATE:     makeField("Date",              "date_order",                         (order) => getOrderDate(order)             ),
        MOBILE:         makeField("Phone / Mobile",    "mobile",                             (order) => getOrderMobile(order)           ),
        CATEGORY:       makeField("Product Category",  "lines.product_id.categ_id.name",     (order) => getOrderCategories(order)       ),
        AMOUNT:         makeField("Bill Amount",       "amount_total",                       (order) => String(getOrderAmountNum(order)) ),
        CUSTOM_FILTER:  makeField("Custom Filter...", "",                                    ()      => ""                              ),
    };
}

const EXACT_FIELDS = new Set(["AMOUNT"]);

function sortOrders(orders, ascending = false) {
    return orders.sort((a, b) => {
        const dateA = a.date_order ? new Date(a.date_order) : new Date(0);
        const dateB = b.date_order ? new Date(b.date_order) : new Date(0);
        if (dateA.getTime() !== dateB.getTime()) return ascending ? dateA - dateB : dateB - dateA;
        const nameA = parseInt(a.pos_reference?.replace(/\D/g, "")) || 0;
        const nameB = parseInt(b.pos_reference?.replace(/\D/g, "")) || 0;
        return ascending ? nameA - nameB : nameB - nameA;
    });
}

// ═══════════════════════════════════════════════════════════════════════════════
// PATCH
// ═══════════════════════════════════════════════════════════════════════════════

patch(TicketScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this._customFilter = null;
    },

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

    async onSearch(search) {
        if (search?.fieldName === "CUSTOM_FILTER") {
            const result = await new Promise((resolve) => {
                this.dialog.add(
                    NativeCustomFilterDialog,
                    { confirm: (payload) => resolve(payload) },
                    { onClose: () => resolve(null) }
                );
            });

            if (result && result.rules && result.rules.length > 0) {
                this._customFilter = result;
                this.state.filter = "CUSTOM_FILTER";

                if (this.pos.screenState?.ticketScreen) {
                    this.pos.screenState.ticketScreen.totalCount = 0;
                    this.pos.screenState.ticketScreen.offsetByDomain = {};
                }

                // Do NOT directly mutate this.state.search — it destroys SearchBar's
                // reactive reference. Instead call super.onSearch() with a safe field
                // so SearchBar resets through its own code path.
                const fields    = this.getSearchFields ? this.getSearchFields() : {};
                const safeField = Object.keys(fields).find((k) => k !== "CUSTOM_FILTER") || "RECEIPT_NUMBER";
                await super.onSearch({ fieldName: safeField, searchTerm: "" });
            }
            return;
        }
        return super.onSearch(search);
    },

    _getFilterOptions() {
        let options;
        try { options = super._getFilterOptions(); } catch (_e) { options = new Map(); }
        if (!options) options = new Map();
        return options;
    },

    async onFilterSelected(selectedFilter) {
        this._customFilter = null;
        return super.onFilterSelected(selectedFilter);
    },

    getFilteredOrderList() {
        const { fieldName, searchTerm } = this.state.search || {};

        // ── Bill Amount exact-match fast path ──
        if (EXACT_FIELDS.has(fieldName) && searchTerm) {
            const orderModel = this.pos.models["pos.order"];
            let orders = this.state.filter === "SYNCED"
                ? orderModel.filter((o) => o.finalized && o.uiState.displayed)
                : orderModel.filter(this.activeOrderFilter);
            if (this.state.filter && !["ACTIVE_ORDERS", "SYNCED", "CUSTOM_FILTER"].includes(this.state.filter)) {
                orders = orders.filter((order) => {
                    const screen = order.getScreenData();
                    return this._getScreenToStatusMap()[screen.name] === this.state.filter;
                });
            }
            orders = orders.filter((order) => amountMatchesOrder(order, searchTerm));
            if (this.state.selectedPreset)
                orders = orders.filter((order) => order.preset_id?.id === this.state.selectedPreset.id);
            if (this.state.filter === "SYNCED")
                return sortOrders(orders).slice((this.state.page - 1) * this.state.nbrByPage, this.state.page * this.state.nbrByPage);
            if (this.pos.screenState?.ticketScreen)
                this.pos.screenState.ticketScreen.totalCount = orders.length;
            return sortOrders(orders, true).slice((this.state.page - 1) * this.state.nbrByPage, this.state.page * this.state.nbrByPage);
        }

        // ── Multi-rule custom filter ──
        if (this.state.filter === "CUSTOM_FILTER" && this._customFilter) {
            const orderModel = this.pos.models["pos.order"];
            let orders = orderModel.filter(this.activeOrderFilter);
            orders = orders.filter((order) => matchesNativeFilter(order, this._customFilter));
            if (this.state.selectedPreset)
                orders = orders.filter((order) => order.preset_id?.id === this.state.selectedPreset.id);
            if (this.pos.screenState?.ticketScreen)
                this.pos.screenState.ticketScreen.totalCount = orders.length;
            return sortOrders(orders, true).slice((this.state.page - 1) * this.state.nbrByPage, this.state.page * this.state.nbrByPage);
        }

        return super.getFilteredOrderList();
    },

    _doesOrderPassFilter(order, { fieldName, searchTerm }) {
        if (fieldName === "AMOUNT") return amountMatchesOrder(order, searchTerm);
        try { return super._doesOrderPassFilter(order, { fieldName, searchTerm }); }
        catch (_e) { return true; }
    },

    filterOrderBySearch(order, searchDetails) {
        if (searchDetails?.fieldName === "AMOUNT") return amountMatchesOrder(order, searchDetails.searchTerm);
        try { return super.filterOrderBySearch(order, searchDetails); }
        catch (_e) { return true; }
    },
});