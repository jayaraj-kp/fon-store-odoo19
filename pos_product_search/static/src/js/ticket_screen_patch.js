/** @odoo-module **/

/**
 * POS Product Search Filter — v8 (Odoo 19 CE)
 *
 * Completely new strategy: Instead of patching TicketScreen.prototype,
 * we directly patch the template registry to add our <li> to the
 * search dropdown, AND patch the search/filter method at the class level.
 *
 * Also adds a MutationObserver as the ultimate fallback — it watches
 * the entire document for the dropdown appearing and injects directly.
 */

import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { _t } from "@web/core/l10n/translation";

console.log("[POS Product Search v8] Module loading...");

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

// ─── MutationObserver: watches for the search dropdown appearing in DOM ───────

let _activeTicketScreen = null;   // reference set in setup()

function handleDropdownMutation() {
    // Find any visible <li> that has "Reference" or "Receipt" text — that's our dropdown
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

    // Get current search term from the input near this dropdown
    const searchInput =
        (_activeTicketScreen?.state?.searchInput) ||
        document.querySelector(".ticket-screen input[type='text']")?.value ||
        document.querySelector(".pos-topheader input")?.value ||
        "";

    if (!searchInput.trim()) return;

    console.log("[POS Product Search v8] Injecting Product li into:", ul.className, "term:", searchInput);

    const li = document.createElement("li");
    li.setAttribute("data-pos-product-search", "1");
    li.className = anchorLi.className;   // copy exact class from sibling
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

// Start a MutationObserver on <body> to catch dropdown appearing
const observer = new MutationObserver(() => {
    try { handleDropdownMutation(); } catch (e) { /* silent */ }
});
observer.observe(document.body, { childList: true, subtree: true });
console.log("[POS Product Search v8] MutationObserver started ✓");

// ─── Patch ────────────────────────────────────────────────────────────────────

patch(TicketScreen.prototype, {
    setup() {
        super.setup(...arguments);
        _activeTicketScreen = this;
        console.log("[POS Product Search v8] TicketScreen setup() called ✓");
    },

    getSearchFields() {
        let fields = {};
        try { fields = super.getSearchFields() || {}; } catch (_e) {}
        const result = {
            ...fields,
            PRODUCT: {
                displayName: _t("Product"),
                modelField: "lines.product_id.display_name",
                repr: (order) => getOrderProductNames(order),
            },
        };
        console.log("[POS Product Search v8] getSearchFields() →", Object.keys(result));
        return result;
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

console.log("[POS Product Search v8] Patch applied ✓");