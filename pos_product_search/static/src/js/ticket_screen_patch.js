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

let _activeTicketScreen = null;

function injectProductLi() {
    // Target the exact search dropdown — class confirmed from diagnostic
    const ul = document.querySelector("ul.py-1.px-0.small");
    if (!ul) return;

    // Remove stale injected item (search term may have changed)
    ul.querySelector("[data-pos-product-search]")?.remove();

    const searchInput = (_activeTicketScreen?.state?.searchInput || "").trim();
    if (!searchInput) return;

    // Already has our item with same term? skip
    const existing = ul.querySelector("[data-pos-product-search]");
    if (existing) return;

    const anchorLi = ul.querySelector("li");
    const li = document.createElement("li");
    li.setAttribute("data-pos-product-search", "1");
    li.className = anchorLi ? anchorLi.className : "";
    li.style.cursor = "pointer";
    li.innerHTML = `<span class="field">${_t("Product")}</span><span>: </span><span class="term text-primary fw-bolder">${searchInput}</span>`;

    li.addEventListener("mousedown", (e) => {
        e.preventDefault();
        e.stopPropagation();
        const comp = _activeTicketScreen;
        if (!comp) return;
        if (typeof comp.onClickSearchField === "function") {
            comp.onClickSearchField("PRODUCT");
        } else if (typeof comp.setSearchField === "function") {
            comp.setSearchField("PRODUCT");
        }
    });

    ul.appendChild(li);
}

function startObserver() {
    const target = document.body || document.documentElement;
    new MutationObserver(() => {
        try { injectProductLi(); } catch (_e) {}
    }).observe(target, { childList: true, subtree: true });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", startObserver);
} else {
    startObserver();
}

patch(TicketScreen.prototype, {
    setup() {
        super.setup(...arguments);
        _activeTicketScreen = this;
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
        };
    },

    _doesOrderPassFilter(order, { fieldName, searchTerm }) {
        if (fieldName === "PRODUCT") {
            const term = (searchTerm || "").toLowerCase().trim();
            if (!term) return true;
            return getOrderProductNames(order).includes(term);
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