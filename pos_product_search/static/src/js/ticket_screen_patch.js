///** @odoo-module **/
//
//import { patch } from "@web/core/utils/patch";
//import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
//import { Component, useState, xml } from "@odoo/owl";
//import { Dialog } from "@web/core/dialog/dialog";
//import { _t } from "@web/core/l10n/translation";
//
//// ═══════════════════════════════════════════════════════════════════════════════
//// FIELD DEFINITIONS
//// ═══════════════════════════════════════════════════════════════════════════════
//
//const FIELD_DEFS = [
//    { key: "amount_total",   label: "Bill Amount",       type: "number" },
//    { key: "partner_name",   label: "Customer Name",     type: "text"   },
//    { key: "mobile",         label: "Phone / Mobile",    type: "text"   },
//    { key: "product_name",   label: "Product Name",      type: "text"   },
//    { key: "payment_method", label: "Payment Method",    type: "text"   },
//    { key: "date_order",     label: "Date (YYYY-MM-DD)", type: "text"   },
//    { key: "category",       label: "Product Category",  type: "text"   },
//    { key: "pos_reference",  label: "Order Reference",   type: "text"   },
//];
//
//const OPERATORS_TEXT = [
//    { key: "ilike",     label: "contains"         },
//    { key: "not ilike", label: "does not contain"  },
//    { key: "=",         label: "is equal to"       },
//    { key: "!=",        label: "is not equal to"   },
//];
//
//const OPERATORS_NUMBER = [
//    { key: "=",  label: "is equal to"                },
//    { key: "!=", label: "is not equal to"             },
//    { key: ">",  label: "is greater than"             },
//    { key: ">=", label: "is greater than or equal to" },
//    { key: "<",  label: "is less than"                },
//    { key: "<=", label: "is less than or equal to"    },
//];
//
//function getOperatorsForField(fieldKey) {
//    const def = FIELD_DEFS.find((f) => f.key === fieldKey);
//    return def && def.type === "number" ? OPERATORS_NUMBER : OPERATORS_TEXT;
//}
//
//function makeRule() {
//    return { id: Date.now() + Math.random(), field: "amount_total", operator: "=", value: "" };
//}
//
//// ═══════════════════════════════════════════════════════════════════════════════
//// CUSTOM FILTER DIALOG
//// ═══════════════════════════════════════════════════════════════════════════════
//
//class NativeCustomFilterDialog extends Component {
//    static components = { Dialog };
//    static props = ["close", "confirm"];
//
//    static template = xml`
//<Dialog title="'Custom Filter'">
//  <div style="min-width:580px;">
//
//    <div class="d-flex align-items-center justify-content-between mb-3">
//      <div class="d-flex align-items-center gap-2 flex-wrap">
//        <span>Match</span>
//        <select class="form-select form-select-sm d-inline-block"
//                style="width:auto"
//                t-model="state.matchMode">
//          <option value="any">any</option>
//          <option value="all">all</option>
//        </select>
//        <span>of the following rules:</span>
//      </div>
//      <div class="form-check form-check-inline m-0">
//        <input class="form-check-input" type="checkbox"
//               id="cfIncludeArchived"
//               t-model="state.includeArchived"/>
//        <label class="form-check-label" for="cfIncludeArchived">
//          Include archived
//        </label>
//      </div>
//    </div>
//
//    <div class="d-flex flex-column gap-2 mb-2">
//      <t t-foreach="state.rules" t-as="rule" t-key="rule.id">
//        <div class="d-flex align-items-center gap-2">
//
//          <select class="form-select form-select-sm"
//                  style="min-width:160px; flex:1"
//                  t-att-value="rule.field"
//                  t-on-change="(ev) => this.onFieldChange(rule, ev)">
//            <t t-foreach="fieldDefs" t-as="fd" t-key="fd.key">
//              <option t-att-value="fd.key"
//                      t-att-selected="fd.key === rule.field"
//                      t-esc="fd.label"/>
//            </t>
//          </select>
//
//          <select class="form-select form-select-sm"
//                  style="min-width:180px; flex:1"
//                  t-att-value="rule.operator"
//                  t-on-change="(ev) => this.onOperatorChange(rule, ev)">
//            <t t-foreach="getOperators(rule.field)" t-as="op" t-key="op.key">
//              <option t-att-value="op.key"
//                      t-att-selected="op.key === rule.operator"
//                      t-esc="op.label"/>
//            </t>
//          </select>
//
//          <input class="form-control form-control-sm"
//                 style="min-width:120px; flex:1"
//                 type="text"
//                 t-att-value="rule.value"
//                 t-on-input="(ev) => this.onValueInput(rule, ev)"
//                 t-on-keydown="(ev) => this.onKeydown(ev)"
//                 placeholder="Value"/>
//
//          <button class="btn btn-sm btn-light border"
//                  t-att-disabled="state.rules.length === 1 ? true : undefined"
//                  t-on-click="() => this.removeRule(rule)"
//                  title="Remove rule">
//            <i class="fa fa-trash-o"/>
//          </button>
//
//        </div>
//      </t>
//    </div>
//
//    <div class="mb-3">
//      <a href="#" class="text-decoration-none small" t-on-click.prevent="addRule">
//        <i class="fa fa-plus me-1"/>New Rule
//      </a>
//    </div>
//
//    <div class="d-flex gap-2">
//      <button class="btn btn-primary btn-sm"
//              t-att-disabled="!canSearch ? true : undefined"
//              t-on-click="onSearch">
//        Search
//      </button>
//      <button class="btn btn-secondary btn-sm"
//              t-on-click="() => props.close()">
//        Discard
//      </button>
//    </div>
//
//  </div>
//</Dialog>
//    `;
//
//    setup() {
//        this.fieldDefs = FIELD_DEFS;
//        this.state = useState({
//            matchMode:       "any",
//            includeArchived: false,
//            rules:           [makeRule()],
//        });
//    }
//
//    getOperators(fieldKey)     { return getOperatorsForField(fieldKey); }
//    onFieldChange(rule, ev)    { rule.field = ev.target.value; rule.operator = getOperatorsForField(rule.field)[0].key; }
//    onOperatorChange(rule, ev) { rule.operator = ev.target.value; }
//    onValueInput(rule, ev)     { rule.value   = ev.target.value; }
//
//    addRule() { this.state.rules.push(makeRule()); }
//
//    removeRule(rule) {
//        if (this.state.rules.length <= 1) return;
//        const idx = this.state.rules.findIndex((r) => r.id === rule.id);
//        if (idx !== -1) this.state.rules.splice(idx, 1);
//    }
//
//    get canSearch() { return this.state.rules.some((r) => r.value.trim() !== ""); }
//    onKeydown(ev)   { if (ev.key === "Enter" && this.canSearch) this.onSearch(); }
//
//    onSearch() {
//        if (!this.canSearch) return;
//        this.props.confirm({
//            matchMode:       this.state.matchMode,
//            includeArchived: this.state.includeArchived,
//            rules: this.state.rules
//                .filter((r) => r.value.trim() !== "")
//                .map((r) => ({ field: r.field, operator: r.operator, value: r.value.trim() })),
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
//            (line.product  && (line.product.display_name  || line.product.name))  || ""
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
//            (line.payment_method   && (line.payment_method.name   || line.payment_method.display_name))   ||
//            line.name || ""
//        ).filter(Boolean).join(" ").toLowerCase();
//}
//
//function getOrderDate(order) {
//    const raw = order.date_order || order.creation_date || order.date || "";
//    if (!raw) return "";
//    try {
//        const d   = new Date(raw);
//        const pad = (n) => String(n).padStart(2, "0");
//        const yyyy = d.getFullYear(), mm = pad(d.getMonth() + 1), dd = pad(d.getDate());
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
//    const cats  = new Set();
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
//function getFieldValue(order, fieldKey) {
//    switch (fieldKey) {
//        case "amount_total":   return getOrderAmountNum(order);
//        case "partner_name":   return ((typeof order.getPartnerName === "function" && order.getPartnerName()) || order.partner_id?.name || "").toLowerCase();
//        case "mobile":         return getOrderMobile(order);
//        case "product_name":   return getOrderProductNames(order);
//        case "payment_method": return getOrderPaymentMethods(order);
//        case "date_order":     return getOrderDate(order);
//        case "category":       return getOrderCategories(order);
//        case "pos_reference":  return (order.pos_reference || order.name || "").toLowerCase();
//        default:               return "";
//    }
//}
//
//function applyOperator(orderVal, operator, rawValue) {
//    const isNum = typeof orderVal === "number";
//    const val   = isNum ? parseFloat(rawValue) : rawValue.toLowerCase().trim();
//    if (isNum && isNaN(val)) return false;
//    switch (operator) {
//        case "=":         return isNum ? Math.abs(orderVal - val) < 0.001 : orderVal === val;
//        case "!=":        return isNum ? Math.abs(orderVal - val) >= 0.001 : orderVal !== val;
//        case ">":         return orderVal > val;
//        case ">=":        return orderVal >= val;
//        case "<":         return orderVal < val;
//        case "<=":        return orderVal <= val;
//        case "ilike":     return String(orderVal).includes(String(val));
//        case "not ilike": return !String(orderVal).includes(String(val));
//        default:          return true;
//    }
//}
//
//function matchesNativeFilter(order, payload) {
//    if (!payload || !payload.rules || payload.rules.length === 0) return true;
//    const results = payload.rules.map((rule) =>
//        applyOperator(getFieldValue(order, rule.field), rule.operator, rule.value)
//    );
//    return payload.matchMode === "all" ? results.every(Boolean) : results.some(Boolean);
//}
//
//function buildSearchFields(existingFields) {
//    return {
//        ...existingFields,
//        PRODUCT:        { displayName: _t("Product"),          modelField: "lines.product_id.display_name",      repr: (order) => getOrderProductNames(order)    },
//        PAYMENT_METHOD: { displayName: _t("Payment Method"),   modelField: "payment_ids.payment_method_id.name", repr: (order) => getOrderPaymentMethods(order)  },
//        ORDER_DATE:     { displayName: _t("Date"),             modelField: "date_order",                         repr: (order) => getOrderDate(order)             },
//        MOBILE:         { displayName: _t("Phone / Mobile"),   modelField: "mobile",                             repr: (order) => getOrderMobile(order)           },
//        CATEGORY:       { displayName: _t("Product Category"), modelField: "lines.product_id.categ_id.name",     repr: (order) => getOrderCategories(order)       },
//        AMOUNT:         { displayName: _t("Bill Amount"),      modelField: "amount_total",                       repr: (order) => String(getOrderAmountNum(order)) },
//        CUSTOM_FILTER:  { displayName: _t("Custom Filter..."), modelField: "",                                   repr: ()      => ""                              },
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
//    async onSearch(search) {
//        if (search?.fieldName === "CUSTOM_FILTER") {
//            const result = await new Promise((resolve) => {
//                this.dialog.add(
//                    NativeCustomFilterDialog,
//                    { confirm: (payload) => resolve(payload) },
//                    { onClose: () => resolve(null) }
//                );
//            });
//
//            if (result && result.rules && result.rules.length > 0) {
//                this._customFilter = result;
//
//                // ┌─────────────────────────────────────────────────────────────┐
//                // │  ROOT CAUSE OF THE CRASH — explained:                       │
//                // │                                                             │
//                // │  getSearchBarConfig() (Odoo's own, not patched) does:       │
//                // │    defaultFilter: this.state.filter                         │
//                // │                                                             │
//                // │  SearchBar template reads:                                  │
//                // │    filter.options.get(state.selectedFilter).text            │
//                // │                                                             │
//                // │  If we set this.state.filter = "CUSTOM_FILTER", that key   │
//                // │  does NOT exist in the filter.options Map returned by       │
//                // │  _getFilterOptions() → .get() returns undefined             │
//                // │  → undefined.text → TypeError CRASH.                       │
//                // │                                                             │
//                // │  FIX: NEVER set state.filter to "CUSTOM_FILTER".           │
//                // │  Use this._customFilter as the sole source of truth.       │
//                // └─────────────────────────────────────────────────────────────┘
//
//                // Reset search bar cleanly (do NOT touch this.state.filter)
//                const fields    = this.getSearchFields ? this.getSearchFields() : {};
//                const safeField = Object.keys(fields).find((k) => k !== "CUSTOM_FILTER") || "RECEIPT_NUMBER";
//                await super.onSearch({ fieldName: safeField, searchTerm: "" });
//            }
//            return;
//        }
//
//        // Any regular search clears the custom filter
//        this._customFilter = null;
//        return super.onSearch(search);
//    },
//
//    async onFilterSelected(selectedFilter) {
//        // Switching filter tabs clears any active custom filter
//        this._customFilter = null;
//        return super.onFilterSelected(selectedFilter);
//    },
//
//    getFilteredOrderList() {
//        const { fieldName, searchTerm } = this.state.search || {};
//
//        // ── Custom filter (highest priority) ─────────────────────────────────
//        // Check this._customFilter directly — NOT state.filter — because
//        // setting state.filter="CUSTOM_FILTER" crashes SearchBar (see above).
//        if (this._customFilter && this._customFilter.rules && this._customFilter.rules.length > 0) {
//            const orderModel = this.pos.models["pos.order"];
//            let orders = orderModel.filter(this.activeOrderFilter);
//            orders = orders.filter((order) => matchesNativeFilter(order, this._customFilter));
//            if (this.state.selectedPreset)
//                orders = orders.filter((order) => order.preset_id?.id === this.state.selectedPreset.id);
//            return sortOrders(orders, true).slice(
//                (this.state.page - 1) * this.state.nbrByPage,
//                this.state.page * this.state.nbrByPage
//            );
//        }
//
//        // ── Bill Amount exact-match fast path ─────────────────────────────────
//        if (EXACT_FIELDS.has(fieldName) && searchTerm) {
//            const orderModel = this.pos.models["pos.order"];
//            let orders = this.state.filter === "SYNCED"
//                ? orderModel.filter((o) => o.finalized && o.uiState.displayed)
//                : orderModel.filter(this.activeOrderFilter);
//            if (this.state.filter && !["ACTIVE_ORDERS", "SYNCED"].includes(this.state.filter)) {
//                orders = orders.filter((order) => {
//                    const screen = order.getScreenData();
//                    return this._getScreenToStatusMap()[screen.name] === this.state.filter;
//                });
//            }
//            orders = orders.filter((order) => amountMatchesOrder(order, searchTerm));
//            if (this.state.selectedPreset)
//                orders = orders.filter((order) => order.preset_id?.id === this.state.selectedPreset.id);
//            return sortOrders(orders, this.state.filter !== "SYNCED").slice(
//                (this.state.page - 1) * this.state.nbrByPage,
//                this.state.page * this.state.nbrByPage
//            );
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
import { useState, useRef, useEffect } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { Component, xml } from "@odoo/owl";

// ─────────────────────────────────────────────
//  Custom Filter Dialog Component
// ─────────────────────────────────────────────
class CustomFilterDialog extends Component {
    static template = xml`
        <Dialog title="'Custom Filter'" size="'md'">
            <div class="p-3">
                <!-- Match any/all -->
                <div class="d-flex align-items-center gap-2 mb-3">
                    <span>Match</span>
                    <select class="form-select w-auto" t-model="state.matchMode">
                        <option value="any">any</option>
                        <option value="all">all</option>
                    </select>
                    <span>of the following rules:</span>
                    <div class="ms-auto form-check">
                        <input class="form-check-input" type="checkbox" id="includeArchived"
                            t-model="state.includeArchived"/>
                        <label class="form-check-label" for="includeArchived">Include archived</label>
                    </div>
                </div>

                <!-- Rules -->
                <div t-foreach="state.rules" t-as="rule" t-key="rule.id" class="d-flex align-items-center gap-2 mb-2">
                    <!-- Field selector -->
                    <select class="form-select" t-model="rule.field" t-on-change="() => this.onFieldChange(rule)">
                        <option value="amount_total">Bill Amount</option>
                        <option value="partner_id.name">Customer Name</option>
                        <option value="partner_id.mobile">Mobile</option>
                        <option value="lines.product_id.name">Product</option>
                        <option value="lines.product_id.categ_id.name">Category</option>
                        <option value="payment_ids.payment_method_id.name">Payment Method</option>
                        <option value="name">Order Reference</option>
                    </select>

                    <!-- Operator selector -->
                    <select class="form-select" t-model="rule.operator">
                        <t t-if="isNumericField(rule.field)">
                            <option value="=">=  (is equal to)</option>
                            <option value="!=">!= (is not equal to)</option>
                            <option value=">">&gt; (greater than)</option>
                            <option value=">=">&gt;= (greater than or equal)</option>
                            <option value="&lt;">&lt; (less than)</option>
                            <option value="&lt;=">&lt;= (less than or equal)</option>
                        </t>
                        <t t-else="">
                            <option value="ilike">contains</option>
                            <option value="not ilike">does not contain</option>
                            <option value="=">is equal to</option>
                            <option value="!=">is not equal to</option>
                        </t>
                    </select>

                    <!-- Value input -->
                    <input class="form-control"
                        t-att-type="isNumericField(rule.field) ? 'number' : 'text'"
                        t-model="rule.value"
                        placeholder="Value"/>

                    <!-- Delete rule -->
                    <button class="btn btn-sm btn-outline-danger" t-on-click="() => this.removeRule(rule.id)">
                        <i class="fa fa-trash"/>
                    </button>
                </div>

                <!-- Add Rule -->
                <button class="btn btn-sm btn-link text-primary" t-on-click="addRule">
                    <i class="fa fa-plus"/> New Rule
                </button>
            </div>

            <t t-set-slot="footer">
                <button class="btn btn-primary" t-on-click="onSearch">Search</button>
                <button class="btn btn-secondary ms-2" t-on-click="onDiscard">Discard</button>
            </t>
        </Dialog>
    `;

    static components = { Dialog };
    static props = {
        onSearch: Function,
        close: Function,
    };

    setup() {
        this.state = useState({
            matchMode: "any",
            includeArchived: false,
            rules: [
                { id: 1, field: "amount_total", operator: "=", value: "" },
            ],
        });
        this._nextId = 2;
    }

    isNumericField(field) {
        return ["amount_total"].includes(field);
    }

    onFieldChange(rule) {
        // Reset operator when switching between numeric/text
        if (this.isNumericField(rule.field)) {
            rule.operator = "=";
        } else {
            rule.operator = "ilike";
        }
        rule.value = "";
    }

    addRule() {
        this.state.rules.push({
            id: this._nextId++,
            field: "amount_total",
            operator: "=",
            value: "",
        });
    }

    removeRule(id) {
        const idx = this.state.rules.findIndex((r) => r.id === id);
        if (idx !== -1) this.state.rules.splice(idx, 1);
    }

    /**
     * Build an Odoo domain array from the rules.
     * Handles dotted paths (relational fields) by using the correct domain syntax.
     */
    _buildDomain() {
        const conditions = this.state.rules
            .filter((r) => r.value !== "" && r.value !== null && r.value !== undefined)
            .map((r) => {
                let value = r.value;
                // Cast numeric fields to float
                if (this.isNumericField(r.field)) {
                    value = parseFloat(value);
                    if (isNaN(value)) return null;
                }
                return [r.field, r.operator, value];
            })
            .filter(Boolean);

        if (conditions.length === 0) return [];

        if (conditions.length === 1) return [conditions[0]];

        // Build domain with AND/OR logic
        const logicOp = this.state.matchMode === "any" ? "|" : "&";
        const domain = [];
        for (let i = 0; i < conditions.length - 1; i++) {
            domain.push(logicOp);
        }
        return domain.concat(conditions);
    }

    onSearch() {
        const domain = this._buildDomain();
        const includeArchived = this.state.includeArchived;
        this.props.onSearch({ domain, includeArchived });
        this.props.close();
    }

    onDiscard() {
        this.props.close();
    }
}

// ─────────────────────────────────────────────
//  TicketScreen Patch
// ─────────────────────────────────────────────
patch(TicketScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
        this.orm = useService("orm");

        // Extra state for our custom filters
        this._customFilterDomain = null;
        this._customFilterActive = false;
    },

    /**
     * Override getFilteredOrderList to apply custom domain via server search.
     * We intercept BEFORE the parent's client-side filter runs.
     */
    get filteredOrderList() {
        // If a custom filter is active, return the server-fetched results
        // stored in _customFilterOrders (set by _applyCustomFilter)
        if (this._customFilterActive && this._customFilterOrders) {
            return this._customFilterOrders;
        }
        // Otherwise fall back to the standard behaviour
        return super.filteredOrderList;
    },

    /**
     * Called when the user clicks "Custom Filter" from the search dropdown.
     */
    openCustomFilter() {
        this.dialog.add(CustomFilterDialog, {
            onSearch: ({ domain, includeArchived }) => {
                this._applyCustomFilter(domain, includeArchived);
            },
        });
    },

    /**
     * Run a server-side search with the domain and cache results.
     */
    async _applyCustomFilter(domain, includeArchived) {
        if (!domain || domain.length === 0) {
            this._customFilterActive = false;
            this._customFilterOrders = null;
            return;
        }

        try {
            // Always scope to the current POS session
            const sessionDomain = [
                ["session_id", "=", this.pos.session.id],
                ...domain,
            ];

            const context = {};
            if (includeArchived) {
                context.active_test = false;
            }

            // Fetch matching order IDs from the server
            const orderIds = await this.orm.search("pos.order", sessionDomain, {
                context,
                limit: 200,
            });

            if (orderIds.length === 0) {
                this._customFilterActive = true;
                this._customFilterOrders = [];
                return;
            }

            // Fetch full order data
            const orders = await this.orm.read(
                "pos.order",
                orderIds,
                [
                    "name",
                    "date_order",
                    "partner_id",
                    "amount_total",
                    "state",
                    "payment_ids",
                    "lines",
                    "session_id",
                ],
                { context }
            );

            // Map server records to the POS order objects already in memory where possible,
            // otherwise use the raw server data
            const posOrderMap = {};
            for (const order of this.pos.orders) {
                if (order.server_id || order.id) {
                    posOrderMap[order.server_id || order.id] = order;
                }
            }

            const result = orders.map((serverOrder) => {
                return posOrderMap[serverOrder.id] || serverOrder;
            });

            this._customFilterActive = true;
            this._customFilterOrders = result;
        } catch (e) {
            console.error("[CustomFilter] Server search failed:", e);
            this._customFilterActive = false;
            this._customFilterOrders = null;
        }
    },

    /**
     * Clear the custom filter (e.g., when search input is cleared).
     */
    clearCustomFilter() {
        this._customFilterActive = false;
        this._customFilterOrders = null;
    },

    // ── Search field helpers (kept from original) ──────────────────────────

    getSearchFields() {
        const fields = super.getSearchFields ? super.getSearchFields() : [];
        // Add "Custom Filter" entry if not already present
        if (!fields.find((f) => f.fieldName === "CUSTOM_FILTER")) {
            fields.push({
                fieldName: "CUSTOM_FILTER",
                displayName: "Custom Filter",
                searchIcon: "fa-filter",
            });
        }
        return fields;
    },

    onClickSearchField(fieldName) {
        if (fieldName === "CUSTOM_FILTER") {
            this.openCustomFilter();
            return;
        }
        if (super.onClickSearchField) {
            super.onClickSearchField(fieldName);
        }
    },
});