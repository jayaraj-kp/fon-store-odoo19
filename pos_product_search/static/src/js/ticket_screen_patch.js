/** @odoo-module **/

/**
 * POS Product Search Filter — v7 (Odoo 19 CE)
 * - Adds diagnostic logging so we can see the exact DOM structure
 * - Tries ALL possible ul/list elements and logs what it finds
 */

import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { _t } from "@web/core/l10n/translation";
import { onMounted, onPatched } from "@odoo/owl";

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

/**
 * DIAGNOSTIC: logs the full inner HTML of the dropdown area
 * so we can identify the exact selector to use.
 */
function diagnoseDom(rootEl) {
    console.group("[POS Product Search] DOM Diagnostic");
    console.log("Root el tag:", rootEl?.tagName, rootEl?.className);

    // Log all <ul> elements found inside the component
    const uls = rootEl?.querySelectorAll("ul") || [];
    console.log(`Found ${uls.length} <ul> element(s):`);
    uls.forEach((ul, i) => {
        console.log(`  ul[${i}] class="${ul.className}" id="${ul.id}" children=${ul.children.length}`);
        console.log(`  ul[${i}] outerHTML:`, ul.outerHTML.substring(0, 500));
    });

    // Log all <li> elements (to see existing search field items)
    const lis = rootEl?.querySelectorAll("li") || [];
    console.log(`Found ${lis.length} <li> element(s):`);
    lis.forEach((li, i) => {
        console.log(`  li[${i}] class="${li.className}" text="${li.textContent.trim().substring(0, 80)}"`);
    });

    // Also log elements with "search" in class or id
    const searchEls = rootEl?.querySelectorAll("[class*='search'],[id*='search']") || [];
    console.log(`Found ${searchEls.length} element(s) with 'search' in class/id:`);
    searchEls.forEach((el, i) => {
        console.log(`  [${i}] <${el.tagName.toLowerCase()}> class="${el.className}"`);
    });

    console.groupEnd();
}

function injectProductLi(component) {
    const root = component.el || component.__owl__?.el;
    if (!root) return;

    const inputVal = (component.state?.searchInput || "").trim();

    // Run diagnostic every time input has a value (throttle to avoid spam)
    if (inputVal && !component._posSearchDiagDone) {
        diagnoseDom(root);
        component._posSearchDiagDone = true;
    }
    if (!inputVal) {
        component._posSearchDiagDone = false;
    }

    // Try to find the dropdown container — check ALL possible selectors
    const selectors = [
        "ul.dropdown-menu",
        "ul.o_search_dropdown",
        "ul.list-unstyled",
        "ul.py-1",
        "ul.p-0",
        "ul.m-0",
        "[class*='dropdown'] ul",
        "[class*='search'] ul",
        ".search-bar ul",
        ".o-search ul",
        "ul",
    ];

    let ul = null;
    for (const sel of selectors) {
        const found = root.querySelector(sel);
        if (found) {
            console.log(`[POS Product Search] Found dropdown using selector: "${sel}"`);
            ul = found;
            break;
        }
    }

    if (!ul) {
        // Last resort: find the <li> that contains "Reference:" and get its parent
        const refLi = Array.from(root.querySelectorAll("li")).find(
            (li) => li.textContent.includes("Reference") || li.textContent.includes("Receipt")
        );
        if (refLi) {
            ul = refLi.parentElement;
            console.log("[POS Product Search] Found dropdown via Reference li parent:", ul?.tagName, ul?.className);
        }
    }

    if (!ul) {
        if (inputVal) console.warn("[POS Product Search] Could not find dropdown ul — check diagnostic above");
        return;
    }

    // Remove stale injected item
    ul.querySelector("[data-pos-product-search]")?.remove();
    if (!inputVal) return;

    const li = document.createElement("li");
    li.setAttribute("data-pos-product-search", "1");
    // Copy classes from a sibling <li> for consistent styling
    const siblingLi = ul.querySelector("li:not([data-pos-product-search])");
    li.className = siblingLi ? siblingLi.className : "ps-5 py-1 text-start cursor-pointer";
    li.style.cursor = "pointer";
    li.innerHTML = `<span class="field">${_t("Product")}</span><span>: </span><span class="term text-primary fw-bolder">${inputVal}</span>`;

    li.addEventListener("mousedown", (e) => {
        // mousedown fires before blur which would close the dropdown
        e.preventDefault();
        if (typeof component.onClickSearchField === "function") {
            component.onClickSearchField("PRODUCT");
        } else if (typeof component.setSearchField === "function") {
            component.setSearchField("PRODUCT");
        } else {
            // Manual fallback: set state directly
            if (component.state) {
                component.state.selectedOrder = null;
                component.state.filter = { fieldName: "PRODUCT", searchTerm: inputVal };
            }
        }
    });

    ul.appendChild(li);
    console.log("[POS Product Search] Product <li> injected into:", ul.tagName, ul.className);
}

patch(TicketScreen.prototype, {
    setup() {
        super.setup(...arguments);
        onMounted(() => injectProductLi(this));
        onPatched(() => injectProductLi(this));
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