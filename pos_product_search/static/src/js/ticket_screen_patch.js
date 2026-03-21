/** @odoo-module **/

/**
 * POS Product Search Filter — v6 (Odoo 19 CE)
 *
 * STRATEGY: Two-pronged approach
 * 1. JS: Patch getSearchFields() so Odoo knows PRODUCT is a valid search field
 *    and can filter orders correctly.
 * 2. JS: Use an OWL lifecycle hook (onMounted/onPatched) to inject the
 *    <li> element directly into the DOM — bypassing the XPath problem entirely.
 *    This way we don't need to know the exact template structure.
 */

import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { _t } from "@web/core/l10n/translation";
import { onMounted, onPatched } from "@odoo/owl";

// ─── Helper ──────────────────────────────────────────────────────────────────

function getOrderProductNames(order) {
    const lines =
        (typeof order.get_orderlines === "function" && order.get_orderlines()) ||
        order.lines ||
        order.orderlines ||
        [];
    return Array.from(lines)
        .map((line) =>
            (typeof line.get_full_product_name === "function" && line.get_full_product_name()) ||
            line.full_product_name ||
            line.product_name ||
            (line.product_id && (line.product_id.display_name || line.product_id.name)) ||
            (line.product && (line.product.display_name || line.product.name)) ||
            ""
        )
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
}

// ─── DOM injection ────────────────────────────────────────────────────────────

/**
 * Find the search dropdown <ul> in the TicketScreen DOM.
 * Tries multiple selectors to be resilient across Odoo 17/18/19 markup variations.
 */
function getDropdownUl(rootEl) {
    if (!rootEl) return null;
    // Try every known selector, most-specific first
    const selectors = [
        "ul.dropdown-menu",
        "ul.o_search_dropdown",
        "ul.list-unstyled",
        "ul.py-1",
        ".search-field-list ul",
        ".ticket-screen-search ul",
        "ul",                        // last resort: first <ul> in the component
    ];
    for (const sel of selectors) {
        const el = rootEl.querySelector(sel);
        if (el) return el;
    }
    return null;
}

/**
 * Inject (or refresh) the "Product" <li> into the dropdown.
 * Idempotent — won't add duplicates.
 */
function injectProductLi(component) {
    const root = component.el || component.__owl__?.el;
    if (!root) return;

    const ul = getDropdownUl(root);
    if (!ul) return;

    // Remove any stale injected item first
    ul.querySelector("[data-pos-product-search]")?.remove();

    // Only show when there's a search term
    const inputVal = component.state?.searchInput || "";
    if (!inputVal.trim()) return;

    const li = document.createElement("li");
    li.setAttribute("data-pos-product-search", "1");
    li.className = "ps-5 py-1 text-start cursor-pointer";
    li.style.cursor = "pointer";
    li.innerHTML = `<span class="field">${_t("Product")}</span><span>: </span><span class="term text-primary fw-bolder">${inputVal}</span>`;

    li.addEventListener("click", () => {
        if (typeof component.onClickSearchField === "function") {
            component.onClickSearchField("PRODUCT");
        } else if (typeof component.setSearchField === "function") {
            component.setSearchField("PRODUCT");
        }
    });

    ul.appendChild(li);
}

// ─── Patch ────────────────────────────────────────────────────────────────────

patch(TicketScreen.prototype, {
    setup() {
        super.setup(...arguments);

        // Inject after every render so the li stays in sync with input state
        onMounted(() => injectProductLi(this));
        onPatched(() => injectProductLi(this));
    },

    // ── Register PRODUCT as a valid search field (for filtering logic) ────────
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
        };
    },

    // ── Odoo 19 filter method ─────────────────────────────────────────────────
    _doesOrderPassFilter(order, { fieldName, searchTerm }) {
        if (fieldName === "PRODUCT") {
            const term = (searchTerm || "").toLowerCase().trim();
            if (!term) return true;
            return getOrderProductNames(order).includes(term);
        }
        try { return super._doesOrderPassFilter(order, { fieldName, searchTerm }); }
        catch (_e) { return true; }
    },

    // ── Odoo 17/18 fallbacks ──────────────────────────────────────────────────
    filterOrderBySearch(order, searchDetails) {
        if (searchDetails?.fieldName === "PRODUCT") {
            const term = (searchDetails.searchTerm || "").toLowerCase().trim();
            if (!term) return true;
            return getOrderProductNames(order).includes(term);
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
        try { return super._searchOrder(order, fieldValue); }
        catch (_e) { return true; }
    },
});