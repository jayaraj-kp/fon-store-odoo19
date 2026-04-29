/** @odoo-module **/

/**
 * User Access & Restrictions — access_restrictions.js
 * Odoo 19 CE compatible
 *
 * STRATEGY:
 * 1. Fetch restriction flags via JSON-RPC on load (cached).
 * 2. Use MutationObserver on the whole document body to catch every DOM change.
 * 3. Apply hiding with multiple selector strategies to handle Odoo 19 menu structure.
 */

import { registry } from "@web/core/registry";

// ─── Cache ──────────────────────────────────────────────────────────────────
let _restrictions = null;

async function getRestrictions() {
    if (_restrictions !== null) return _restrictions;
    try {
        const resp = await fetch("/web/dataset/call_kw", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                jsonrpc: "2.0",
                id: 1,
                method: "call",
                params: {
                    model: "res.users",
                    method: "get_current_user_restrictions",
                    args: [],
                    kwargs: { context: {} },
                },
            }),
        });
        const json = await resp.json();
        _restrictions = json.result || {};
        console.log("[UAR] Restrictions loaded:", _restrictions);
    } catch (e) {
        console.error("[UAR] Failed to load restrictions:", e);
        _restrictions = {};
    }
    return _restrictions;
}

// ─── Menu text → restriction key ─────────────────────────────────────────────
// Use lowercase substrings. We check if the menu element's trimmed text
// STARTS WITH or EQUALS one of these keywords.
const MENU_RULES = [
    // Inventory Operations
    { match: "scrap",                        key: "restrict_scrap_menu" },
    { match: "scraps",                       key: "restrict_scrap_menu" },
    { match: "physical inventory",           key: "restrict_physical_inventory" },
    { match: "inventory adjustments",        key: "restrict_physical_inventory" },
    { match: "replenishment",                key: "restrict_replenishment" },
    { match: "inventory valuation",          key: "restrict_inventory_valuation" },
    { match: "landed costs",                 key: "restrict_landed_costs" },
    // Accounting Reports
    { match: "balance sheet",                key: "restrict_balance_sheet" },
    { match: "profit & loss",                key: "restrict_profit_loss" },
    { match: "profit and loss",              key: "restrict_profit_loss" },
    { match: "partner ledger",               key: "restrict_partner_ledger" },
    { match: "general ledger",               key: "restrict_general_ledger" },
    { match: "trial balance",                key: "restrict_trial_balance" },
    { match: "cash flow statement",          key: "restrict_cash_flow" },
    { match: "cash flow",                    key: "restrict_cash_flow" },
    { match: "aged receivable",              key: "restrict_aged_receivable" },
    { match: "aged payable",                 key: "restrict_aged_payable" },
    { match: "tax report",                   key: "restrict_tax_report" },
    { match: "executive summary",            key: "restrict_executive_summary" },
];

// ─── Product field → restriction key ─────────────────────────────────────────
const FIELD_RULES = [
    { field: "standard_price",    key: "restrict_cost_price" },
    { field: "list_price",        key: "restrict_sales_price" },
    { field: "barcode",           key: "restrict_barcode" },
    { field: "default_code",      key: "restrict_internal_reference" },
    { field: "taxes_id",          key: "restrict_taxes" },
    { field: "supplier_taxes_id", key: "restrict_taxes" },
];

const READONLY_RULES = [
    { field: "standard_price", key: "restrict_cost_price_edit" },
    { field: "list_price",     key: "restrict_sales_price_edit" },
];

// ─── Hide a DOM element safely ────────────────────────────────────────────────
function hide(el) {
    if (el) el.style.setProperty("display", "none", "important");
}

// ─── Find the best container to hide for a menu item ─────────────────────────
function hideMenuItem(el) {
    // Walk up to find li, .o_menu_item, .o_dropdown_item, or any direct parent
    const container =
        el.closest("li") ||
        el.closest(".o_dropdown_item") ||
        el.closest(".o_nav_entry") ||
        el.closest(".o_menu_item") ||
        el.parentElement;
    hide(container || el);
}

// ─── Apply menu restrictions ──────────────────────────────────────────────────
function applyMenus(r) {
    if (!r) return;

    // Cast a wide net for all possible menu/nav elements in Odoo 19
    const candidates = document.querySelectorAll(
        [
            ".o_menu_sections a",
            ".o_menu_sections span",
            ".o_menu_sections .o_nav_entry",
            ".o_menu_sections .o_dropdown_item",
            ".o_menu_sections li",
            ".o_dropdown_menu a",
            ".o_dropdown_menu span",
            ".o_dropdown_menu .o_dropdown_item",
            ".o_main_navbar a",
            ".o_main_navbar .o_nav_entry",
            "[role='menuitem']",
            "[role='menu'] a",
            "[role='menu'] li",
            ".o_app_menu_full a",
            ".o_action_manager a.o_menu_item",
        ].join(", ")
    );

    candidates.forEach((el) => {
        // Get only direct text (exclude children text to avoid parent matching)
        const text = (el.textContent || "").trim().toLowerCase();
        if (!text || text.length > 60) return; // skip containers with lots of text

        for (const rule of MENU_RULES) {
            if (r[rule.key] && text === rule.match) {
                hideMenuItem(el);
                return;
            }
        }
        // Also try contains for partial match
        for (const rule of MENU_RULES) {
            if (r[rule.key] && text.includes(rule.match) && text.length < rule.match.length + 10) {
                hideMenuItem(el);
                return;
            }
        }
    });
}

// ─── Apply product field restrictions ────────────────────────────────────────
function applyFields(r) {
    if (!r) return;

    FIELD_RULES.forEach(({ field, key }) => {
        if (!r[key]) return;
        document.querySelectorAll(
            `.o_field_widget[name="${field}"],` +
            `div[name="${field}"],` +
            `td[name="${field}"]`
        ).forEach((widget) => {
            const row =
                widget.closest(".o_wrap_field") ||
                widget.closest(".o_setting_box") ||
                widget.closest("tr") ||
                widget.closest(".o_cell");
            hide(row || widget);
        });
    });

    READONLY_RULES.forEach(({ field, key }) => {
        if (!r[key]) return;
        document.querySelectorAll(
            `.o_field_widget[name="${field}"] input,` +
            `.o_field_widget[name="${field}"] .o_field_monetary input`
        ).forEach((input) => {
            input.setAttribute("readonly", "readonly");
            input.style.pointerEvents = "none";
            input.style.background = "var(--color-background-secondary)";
        });
    });
}

// ─── Master apply ─────────────────────────────────────────────────────────────
let _applyTimer = null;
async function applyAll() {
    const r = await getRestrictions();
    applyMenus(r);
    applyFields(r);
}

function scheduleApply(delay = 300) {
    clearTimeout(_applyTimer);
    _applyTimer = setTimeout(applyAll, delay);
}

// ─── Odoo service ─────────────────────────────────────────────────────────────
const userAccessRestrictionsService = {
    name: "user_access_restrictions",
    dependencies: [],
    start() {
        // First apply
        scheduleApply(500);
        scheduleApply(1200); // second pass after full render

        // Watch DOM mutations (menus re-render on navigation)
        const observer = new MutationObserver(() => scheduleApply(200));

        const attach = () => {
            const root = document.body;
            if (root) {
                observer.observe(root, { childList: true, subtree: true });
            } else {
                setTimeout(attach, 300);
            }
        };

        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", attach);
        } else {
            attach();
        }

        return {};
    },
};

registry.category("services").add("user_access_restrictions", userAccessRestrictionsService);
