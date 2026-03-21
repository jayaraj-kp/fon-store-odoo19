/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { _t } from "@web/core/l10n/translation";

console.log("[POS Product Search v10] Module loading...");

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
let _lastInjectedUl = null;

function injectProductLi() {
    // Log ALL <li> elements currently in DOM so we can see what text they have
    const allLis = document.querySelectorAll("li");
    if (allLis.length > 0 && allLis.length < 30) {
        // Only log when a small number of <li>s visible (dropdown open)
        const liTexts = Array.from(allLis).map(li => `"${li.textContent.trim().substring(0, 60)}"`);
        console.log("[POS Product Search v10] All <li> texts:", liTexts);
    }

    // Find the dropdown: look for ANY <li> inside a <ul> that is a sibling/child
    // of the search input, OR just find the first <ul> that has multiple <li>s
    // with short text (dropdown items)
    let ul = null;

    // Strategy 1: find a <ul> that contains >1 <li> with text shorter than 80 chars
    document.querySelectorAll("ul").forEach((candidate) => {
        if (ul) return;
        const lis = candidate.querySelectorAll("li");
        if (lis.length >= 2) {
            const allShort = Array.from(lis).every(li => li.textContent.trim().length < 80);
            if (allShort) {
                ul = candidate;
                console.log("[POS Product Search v10] Found ul via short-li heuristic, class:", ul.className);
            }
        }
    });

    // Strategy 2: find <li> whose text ends with the current search term
    if (!ul) {
        const searchInput = (_activeTicketScreen?.state?.searchInput || "").trim();
        if (searchInput) {
            for (const li of allLis) {
                if (li.textContent.trim().endsWith(searchInput)) {
                    ul = li.parentElement;
                    console.log("[POS Product Search v10] Found ul via searchTerm suffix match, class:", ul?.className);
                    break;
                }
            }
        }
    }

    if (!ul) return;

    // Don't re-inject if already done for this ul
    if (ul.querySelector("[data-pos-product-search]")) return;

    const searchInput = (_activeTicketScreen?.state?.searchInput || "").trim();
    if (!searchInput) return;

    console.log("[POS Product Search v10] Injecting Product <li>, term:", searchInput);

    const anchorLi = ul.querySelector("li");
    const li = document.createElement("li");
    li.setAttribute("data-pos-product-search", "1");
    li.className = anchorLi ? anchorLi.className : "ps-5 py-1 text-start cursor-pointer";
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
    _lastInjectedUl = ul;
    console.log("[POS Product Search v10] ✓ Product <li> injected!");
}

function startObserver() {
    const target = document.body || document.documentElement;
    const observer = new MutationObserver(() => {
        try { injectProductLi(); } catch (_e) { console.warn("[POS Product Search v10] observer error:", _e); }
    });
    observer.observe(target, { childList: true, subtree: true });
    console.log("[POS Product Search v10] MutationObserver started on", target.tagName, "✓");
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
        console.log("[POS Product Search v10] TicketScreen setup() ✓");
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

console.log("[POS Product Search v10] Patch applied ✓");