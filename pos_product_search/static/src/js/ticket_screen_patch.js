/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { _t } from "@web/core/l10n/translation";

console.log("[POS Product Search v9] Module loading...");

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

// ─── Active component reference ───────────────────────────────────────────────
let _activeTicketScreen = null;

// ─── Dropdown injection ───────────────────────────────────────────────────────

function injectProductLi() {
    // Find an existing search-field <li> (Reference / Receipt Number)
    const allLis = document.querySelectorAll("li");
    let anchorLi = null;
    for (const li of allLis) {
        const txt = li.textContent || "";
        if (txt.includes("Receipt Number") || txt.includes("Reference:")) {
            anchorLi = li;
            break;
        }
    }
    if (!anchorLi) return;

    const ul = anchorLi.parentElement;
    if (!ul) return;

    // Already injected?
    if (ul.querySelector("[data-pos-product-search]")) return;

    const searchInput = (_activeTicketScreen?.state?.searchInput || "").trim();
    if (!searchInput) return;

    console.log("[POS Product Search v9] Injecting Product li, term:", searchInput);

    const li = document.createElement("li");
    li.setAttribute("data-pos-product-search", "1");
    li.className = anchorLi.className;
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

// ─── MutationObserver — started AFTER DOM is ready ───────────────────────────

function startObserver() {
    const target = document.body || document.documentElement;
    const observer = new MutationObserver(() => {
        try { injectProductLi(); } catch (_e) { /* silent */ }
    });
    observer.observe(target, { childList: true, subtree: true });
    console.log("[POS Product Search v9] MutationObserver started on", target.tagName, "✓");
}

// Defer until DOM is available — works whether body exists yet or not
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", startObserver);
} else {
    // DOM already ready (most likely case in Odoo's module loader)
    startObserver();
}

// ─── Patch ────────────────────────────────────────────────────────────────────

patch(TicketScreen.prototype, {
    setup() {
        super.setup(...arguments);
        _activeTicketScreen = this;
        console.log("[POS Product Search v9] TicketScreen setup() ✓");
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

    // Odoo 19
    _doesOrderPassFilter(order, { fieldName, searchTerm }) {
        if (fieldName === "PRODUCT") {
            const term = (searchTerm || "").toLowerCase().trim();
            if (!term) return true;
            return getOrderProductNames(order).includes(term);
        }
        try { return super._doesOrderPassFilter(order, { fieldName, searchTerm }); }
        catch (_e) { return true; }
    },

    // Odoo 17/18 fallback
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

console.log("[POS Product Search v9] Patch applied ✓");