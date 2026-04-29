/** @odoo-module **/

/**
 * User Access & Restrictions — access_restrictions.js
 *
 * Strategy:
 *   1. On backend load, call get_current_user_restrictions() via JSON-RPC.
 *   2. Cache the result in a module-level variable.
 *   3. After each route/view change, scan the DOM and hide restricted
 *      menu items and product form fields.
 *
 * This is the primary UI enforcement layer.
 * The Python ORM layer (product_template.py, stock_scrap.py) enforces at data level.
 */

import { registry } from "@web/core/registry";

// ─── Restriction cache ───────────────────────────────────────────────────────
let restrictions = null;
let restrictionsLoaded = false;

async function fetchRestrictions() {
    if (restrictionsLoaded) return restrictions;
    try {
        const response = await fetch("/web/dataset/call_kw", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: {
                    model: "res.users",
                    method: "get_current_user_restrictions",
                    args: [],
                    kwargs: {},
                },
            }),
        });
        const data = await response.json();
        restrictions = data.result || {};
    } catch (e) {
        console.warn("[UserRestrictions] Failed to load:", e);
        restrictions = {};
    }
    restrictionsLoaded = true;
    return restrictions;
}

// ─── Menu label → restriction key map ────────────────────────────────────────
const MENU_MAP = [
    // Inventory
    ["scrap",                       "restrict_scrap_menu"],
    ["physical inventory",          "restrict_physical_inventory"],
    ["inventory adjustments",       "restrict_physical_inventory"],
    ["replenishment",               "restrict_replenishment"],
    ["inventory valuation",         "restrict_inventory_valuation"],
    ["landed costs",                "restrict_landed_costs"],
    // Accounting reports
    ["balance sheet",               "restrict_balance_sheet"],
    ["profit & loss",               "restrict_profit_loss"],
    ["profit and loss",             "restrict_profit_loss"],
    ["partner ledger",              "restrict_partner_ledger"],
    ["general ledger",              "restrict_general_ledger"],
    ["trial balance",               "restrict_trial_balance"],
    ["cash flow",                   "restrict_cash_flow"],
    ["aged receivable",             "restrict_aged_receivable"],
    ["aged payable",                "restrict_aged_payable"],
    ["tax report",                  "restrict_tax_report"],
    ["executive summary",           "restrict_executive_summary"],
];

// ─── Product field name → restriction key map ─────────────────────────────────
const FIELD_MAP = [
    ["standard_price",      "restrict_cost_price"],
    ["list_price",          "restrict_sales_price"],
    ["barcode",             "restrict_barcode"],
    ["default_code",        "restrict_internal_reference"],
    ["taxes_id",            "restrict_taxes"],
    ["supplier_taxes_id",   "restrict_taxes"],
];

// ─── Hide menus ───────────────────────────────────────────────────────────────
function applyMenuRestrictions(r) {
    if (!r) return;
    const selectors = [
        ".o_menu_sections .o_nav_entry",
        ".o_menu_sections .o_dropdown_item",
        ".o_dropdown .o_dropdown_item",
        ".o_menuitem",
        "[role='menuitem']",
        ".o_menu_item",
    ].join(", ");

    document.querySelectorAll(selectors).forEach((el) => {
        const label = (el.textContent || "").trim().toLowerCase();
        for (const [keyword, key] of MENU_MAP) {
            if (r[key] && label.includes(keyword)) {
                el.closest("li, .o_menu_item, .o_dropdown_item") ?
                    (el.closest("li, .o_menu_item, .o_dropdown_item").style.display = "none") :
                    (el.style.display = "none");
                break;
            }
        }
    });
}

// ─── Hide product form fields ─────────────────────────────────────────────────
function applyFieldRestrictions(r) {
    if (!r) return;
    for (const [fieldName, key] of FIELD_MAP) {
        if (!r[key]) continue;
        // Find all widgets for this field
        const widgets = document.querySelectorAll(
            `.o_field_widget[name="${fieldName}"],` +
            `[name="${fieldName}"].o_field_widget`
        );
        widgets.forEach((widget) => {
            // Walk up to find the containing row/group cell and hide it
            const row =
                widget.closest(".o_wrap_field") ||
                widget.closest(".o_cell") ||
                widget.closest("td") ||
                widget.closest(".o_setting_box") ||
                widget;
            const container = row.closest("tr") || row.closest(".o_field_widget") || row;
            container.style.display = "none";
        });
    }
}

// ─── Make cost price read-only if only edit is restricted ─────────────────────
function applyReadonlyRestrictions(r) {
    if (!r) return;
    const readonlyMap = [
        ["standard_price", "restrict_cost_price_edit"],
        ["list_price",     "restrict_sales_price_edit"],
    ];
    for (const [fieldName, key] of readonlyMap) {
        if (!r[key]) continue;
        document.querySelectorAll(
            `.o_field_widget[name="${fieldName}"] input,` +
            `.o_field_widget[name="${fieldName}"] .o_field_monetary input`
        ).forEach((input) => {
            input.setAttribute("readonly", "readonly");
            input.style.pointerEvents = "none";
            input.style.backgroundColor = "#f5f5f5";
        });
    }
}

// ─── Main apply function ──────────────────────────────────────────────────────
async function applyAllRestrictions() {
    const r = await fetchRestrictions();
    applyMenuRestrictions(r);
    applyFieldRestrictions(r);
    applyReadonlyRestrictions(r);
}

// ─── Register as an Odoo service ─────────────────────────────────────────────
const userRestrictionsService = {
    name: "user_access_restrictions",
    dependencies: [],
    start() {
        // Apply once on load
        applyAllRestrictions();

        // Re-apply after each navigation (SPA route changes)
        // Odoo 17+ uses history.pushState — observe URL changes
        let lastUrl = location.href;
        const urlObserver = setInterval(() => {
            if (location.href !== lastUrl) {
                lastUrl = location.href;
                // Small delay to let the new view render
                setTimeout(applyAllRestrictions, 400);
                setTimeout(applyAllRestrictions, 900);
            }
        }, 200);

        // Also watch DOM mutations in the main content area
        const mutationObserver = new MutationObserver(() => {
            // Debounce
            clearTimeout(mutationObserver._timer);
            mutationObserver._timer = setTimeout(applyAllRestrictions, 300);
        });

        const startObserver = () => {
            const target = document.querySelector(".o_main_navbar, .o_action_manager, #wrapwrap");
            if (target) {
                mutationObserver.observe(target, { childList: true, subtree: true });
            } else {
                setTimeout(startObserver, 500);
            }
        };

        if (document.readyState === "complete") {
            startObserver();
        } else {
            window.addEventListener("load", startObserver);
        }

        return {};
    },
};

registry.category("services").add("user_access_restrictions", userRestrictionsService);
