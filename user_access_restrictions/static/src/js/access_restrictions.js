///** @odoo-module **/
//
///**
// * User Access & Restrictions — access_restrictions.js
// * Odoo 19 CE compatible
// *
// * STRATEGY:
// * 1. Fetch restriction flags via JSON-RPC on load (cached).
// * 2. Use MutationObserver on the whole document body to catch every DOM change.
// * 3. Apply hiding with multiple selector strategies to handle Odoo 19 menu structure.
// */
//
//import { registry } from "@web/core/registry";
//
//// ─── Cache ──────────────────────────────────────────────────────────────────
//let _restrictions = null;
//
//async function getRestrictions() {
//    if (_restrictions !== null) return _restrictions;
//    try {
//        const resp = await fetch("/web/dataset/call_kw", {
//            method: "POST",
//            headers: { "Content-Type": "application/json" },
//            body: JSON.stringify({
//                jsonrpc: "2.0",
//                id: 1,
//                method: "call",
//                params: {
//                    model: "res.users",
//                    method: "get_current_user_restrictions",
//                    args: [],
//                    kwargs: { context: {} },
//                },
//            }),
//        });
//        const json = await resp.json();
//        _restrictions = json.result || {};
//        console.log("[UAR] Restrictions loaded:", _restrictions);
//    } catch (e) {
//        console.error("[UAR] Failed to load restrictions:", e);
//        _restrictions = {};
//    }
//    return _restrictions;
//}
//
//// ─── Menu text → restriction key ─────────────────────────────────────────────
//// Use lowercase substrings. We check if the menu element's trimmed text
//// STARTS WITH or EQUALS one of these keywords.
//const MENU_RULES = [
//    // Inventory Operations
//    { match: "scrap",                        key: "restrict_scrap_menu" },
//    { match: "scraps",                       key: "restrict_scrap_menu" },
//    { match: "physical inventory",           key: "restrict_physical_inventory" },
//    { match: "inventory adjustments",        key: "restrict_physical_inventory" },
//    { match: "replenishment",                key: "restrict_replenishment" },
//    { match: "inventory valuation",          key: "restrict_inventory_valuation" },
//    { match: "landed costs",                 key: "restrict_landed_costs" },
//    // Accounting Reports
//    { match: "balance sheet",                key: "restrict_balance_sheet" },
//    { match: "profit & loss",                key: "restrict_profit_loss" },
//    { match: "profit and loss",              key: "restrict_profit_loss" },
//    { match: "partner ledger",               key: "restrict_partner_ledger" },
//    { match: "general ledger",               key: "restrict_general_ledger" },
//    { match: "trial balance",                key: "restrict_trial_balance" },
//    { match: "cash flow statement",          key: "restrict_cash_flow" },
//    { match: "cash flow",                    key: "restrict_cash_flow" },
//    { match: "aged receivable",              key: "restrict_aged_receivable" },
//    { match: "aged payable",                 key: "restrict_aged_payable" },
//    { match: "tax report",                   key: "restrict_tax_report" },
//    { match: "executive summary",            key: "restrict_executive_summary" },
//];
//
//// ─── Product field → restriction key ─────────────────────────────────────────
//const FIELD_RULES = [
//    { field: "standard_price",    key: "restrict_cost_price" },
//    { field: "list_price",        key: "restrict_sales_price" },
//    { field: "barcode",           key: "restrict_barcode" },
//    { field: "default_code",      key: "restrict_internal_reference" },
//    { field: "taxes_id",          key: "restrict_taxes" },
//    { field: "supplier_taxes_id", key: "restrict_taxes" },
//];
//
//const READONLY_RULES = [
//    { field: "standard_price", key: "restrict_cost_price_edit" },
//    { field: "list_price",     key: "restrict_sales_price_edit" },
//];
//
//// ─── Hide a DOM element safely ────────────────────────────────────────────────
//function hide(el) {
//    if (el) el.style.setProperty("display", "none", "important");
//}
//
//// ─── Find the best container to hide for a menu item ─────────────────────────
//function hideMenuItem(el) {
//    // Walk up to find li, .o_menu_item, .o_dropdown_item, or any direct parent
//    const container =
//        el.closest("li") ||
//        el.closest(".o_dropdown_item") ||
//        el.closest(".o_nav_entry") ||
//        el.closest(".o_menu_item") ||
//        el.parentElement;
//    hide(container || el);
//}
//
//// ─── Apply menu restrictions ──────────────────────────────────────────────────
//function applyMenus(r) {
//    if (!r) return;
//
//    // Cast a wide net for all possible menu/nav elements in Odoo 19
//    const candidates = document.querySelectorAll(
//        [
//            ".o_menu_sections a",
//            ".o_menu_sections span",
//            ".o_menu_sections .o_nav_entry",
//            ".o_menu_sections .o_dropdown_item",
//            ".o_menu_sections li",
//            ".o_dropdown_menu a",
//            ".o_dropdown_menu span",
//            ".o_dropdown_menu .o_dropdown_item",
//            ".o_main_navbar a",
//            ".o_main_navbar .o_nav_entry",
//            "[role='menuitem']",
//            "[role='menu'] a",
//            "[role='menu'] li",
//            ".o_app_menu_full a",
//            ".o_action_manager a.o_menu_item",
//        ].join(", ")
//    );
//
//    candidates.forEach((el) => {
//        // Get only direct text (exclude children text to avoid parent matching)
//        const text = (el.textContent || "").trim().toLowerCase();
//        if (!text || text.length > 60) return; // skip containers with lots of text
//
//        for (const rule of MENU_RULES) {
//            if (r[rule.key] && text === rule.match) {
//                hideMenuItem(el);
//                return;
//            }
//        }
//        // Also try contains for partial match
//        for (const rule of MENU_RULES) {
//            if (r[rule.key] && text.includes(rule.match) && text.length < rule.match.length + 10) {
//                hideMenuItem(el);
//                return;
//            }
//        }
//    });
//}
//
//// ─── Apply product field restrictions ────────────────────────────────────────
//function applyFields(r) {
//    if (!r) return;
//
//    FIELD_RULES.forEach(({ field, key }) => {
//        if (!r[key]) return;
//        document.querySelectorAll(
//            `.o_field_widget[name="${field}"],` +
//            `div[name="${field}"],` +
//            `td[name="${field}"]`
//        ).forEach((widget) => {
//            const row =
//                widget.closest(".o_wrap_field") ||
//                widget.closest(".o_setting_box") ||
//                widget.closest("tr") ||
//                widget.closest(".o_cell");
//            hide(row || widget);
//        });
//    });
//
//    READONLY_RULES.forEach(({ field, key }) => {
//        if (!r[key]) return;
//        document.querySelectorAll(
//            `.o_field_widget[name="${field}"] input,` +
//            `.o_field_widget[name="${field}"] .o_field_monetary input`
//        ).forEach((input) => {
//            input.setAttribute("readonly", "readonly");
//            input.style.pointerEvents = "none";
//            input.style.background = "var(--color-background-secondary)";
//        });
//    });
//}
//
//// ─── Master apply ─────────────────────────────────────────────────────────────
//let _applyTimer = null;
//async function applyAll() {
//    const r = await getRestrictions();
//    applyMenus(r);
//    applyFields(r);
//}
//
//function scheduleApply(delay = 300) {
//    clearTimeout(_applyTimer);
//    _applyTimer = setTimeout(applyAll, delay);
//}
//
//// ─── Odoo service ─────────────────────────────────────────────────────────────
//const userAccessRestrictionsService = {
//    name: "user_access_restrictions",
//    dependencies: [],
//    start() {
//        // First apply
//        scheduleApply(500);
//        scheduleApply(1200); // second pass after full render
//
//        // Watch DOM mutations (menus re-render on navigation)
//        const observer = new MutationObserver(() => scheduleApply(200));
//
//        const attach = () => {
//            const root = document.body;
//            if (root) {
//                observer.observe(root, { childList: true, subtree: true });
//            } else {
//                setTimeout(attach, 300);
//            }
//        };
//
//        if (document.readyState === "loading") {
//            document.addEventListener("DOMContentLoaded", attach);
//        } else {
//            attach();
//        }
//
//        return {};
//    },
//};
//
//registry.category("services").add("user_access_restrictions", userAccessRestrictionsService);

/** @odoo-module **/

/**
 * User Access & Restrictions — access_restrictions.js
 * Odoo 19 CE compatible — FIXED v2
 *
 * ROOT CAUSE OF PREVIOUS BUG:
 * Using [role='menuitem'] or .o_main_navbar selectors caught TOP-LEVEL nav items
 * (Reporting, Operations) whose textContent includes all child text, causing the
 * entire parent dropdown to be hidden when a child was restricted.
 *
 * FIX STRATEGY:
 * 1. NEVER query top-level navbar links — only query items INSIDE open dropdowns
 *    (.o_dropdown_menu, .dropdown-menu) or sub-navigation sections.
 * 2. Use direct text node comparison (directText) NOT textContent which includes children.
 * 3. Use data-menu-xmlid attribute matching as first priority — most reliable.
 * 4. Only hide the specific <a> or <li> element, never walk up past the dropdown boundary.
 */

import { registry } from "@web/core/registry";

// ─── Cache ───────────────────────────────────────────────────────────────────
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

// ─── Menu xmlid → restriction key ────────────────────────────────────────────
// Matching by data-menu-xmlid is the most reliable method in Odoo 19.
// These are the actual xmlids from the menu definitions.
const XMLID_RULES = [
    // Inventory
    { xmlid: "stock.action_stock_scrap",                    key: "restrict_scrap_menu" },
    { xmlid: "stock.menu_stock_scrap",                      key: "restrict_scrap_menu" },
    { xmlid: "stock.action_stock_inventory",                key: "restrict_physical_inventory" },
    { xmlid: "stock.menu_action_stock_inventory",           key: "restrict_physical_inventory" },
    { xmlid: "stock.action_orderpoint_form",                key: "restrict_replenishment" },
    { xmlid: "stock.menu_reorderpoint_form",                key: "restrict_replenishment" },
    { xmlid: "stock.action_stock_inventory_form",           key: "restrict_inventory_valuation" },
    { xmlid: "stock.menu_action_inventory_form",            key: "restrict_inventory_valuation" },
    { xmlid: "stock.action_stock_landed_costs",             key: "restrict_landed_costs" },
    { xmlid: "stock.menu_action_stock_landed_costs",        key: "restrict_landed_costs" },
    // Accounting Reports — CE uses ir.actions.client or report actions
    { xmlid: "account.action_account_report_bs",           key: "restrict_balance_sheet" },
    { xmlid: "account.menu_action_report_bs",              key: "restrict_balance_sheet" },
    { xmlid: "account.action_account_report_pl",           key: "restrict_profit_loss" },
    { xmlid: "account.menu_action_report_pl",              key: "restrict_profit_loss" },
    { xmlid: "account.action_account_report_partner_ledger", key: "restrict_partner_ledger" },
    { xmlid: "account.menu_action_report_partner_ledger",  key: "restrict_partner_ledger" },
    { xmlid: "account.action_account_general_ledger",      key: "restrict_general_ledger" },
    { xmlid: "account.menu_action_general_ledger",         key: "restrict_general_ledger" },
    { xmlid: "account.action_account_report_trial_balance", key: "restrict_trial_balance" },
    { xmlid: "account.menu_action_report_trial_balance",   key: "restrict_trial_balance" },
    { xmlid: "account.action_account_cash_flow_report",    key: "restrict_cash_flow" },
    { xmlid: "account.menu_action_cash_flow_report",       key: "restrict_cash_flow" },
    { xmlid: "account.action_account_receivable",          key: "restrict_aged_receivable" },
    { xmlid: "account.menu_action_report_aged_receivable", key: "restrict_aged_receivable" },
    { xmlid: "account.action_account_payable",             key: "restrict_aged_payable" },
    { xmlid: "account.menu_action_report_aged_payable",    key: "restrict_aged_payable" },
    { xmlid: "account.action_account_report_tax",          key: "restrict_tax_report" },
    { xmlid: "account.menu_action_report_tax",             key: "restrict_tax_report" },
    { xmlid: "account.action_account_report_executive_summary", key: "restrict_executive_summary" },
    { xmlid: "account.menu_action_report_executive_summary",    key: "restrict_executive_summary" },
];

// ─── Menu text → restriction key (FALLBACK — leaf items only) ─────────────────
// IMPORTANT: These match only DIRECT text of the element (not children).
// Only used when xmlid matching fails.
const TEXT_RULES = [
    // Inventory — exact leaf menu labels
    { match: "scrap",                     key: "restrict_scrap_menu" },
    { match: "scraps",                    key: "restrict_scrap_menu" },
    { match: "physical inventory",        key: "restrict_physical_inventory" },
    { match: "inventory adjustments",     key: "restrict_physical_inventory" },
    { match: "replenishment",             key: "restrict_replenishment" },
    { match: "inventory valuation",       key: "restrict_inventory_valuation" },
    { match: "landed costs",              key: "restrict_landed_costs" },
    // Accounting Reports — exact leaf menu labels
    { match: "balance sheet",             key: "restrict_balance_sheet" },
    { match: "profit & loss",             key: "restrict_profit_loss" },
    { match: "profit and loss",           key: "restrict_profit_loss" },
    { match: "partner ledger",            key: "restrict_partner_ledger" },
    { match: "general ledger",            key: "restrict_general_ledger" },
    { match: "trial balance",             key: "restrict_trial_balance" },
    { match: "cash flow statement",       key: "restrict_cash_flow" },
    { match: "cash flow",                 key: "restrict_cash_flow" },
    { match: "aged receivable",           key: "restrict_aged_receivable" },
    { match: "aged payable",              key: "restrict_aged_payable" },
    { match: "tax report",                key: "restrict_tax_report" },
    { match: "executive summary",         key: "restrict_executive_summary" },
];

// ─── Get DIRECT text only (not from child elements) ───────────────────────────
// This is the critical fix: textContent includes ALL descendant text,
// so a parent "Operations" node would match "scrap" because Scrap is a child.
// directText reads only the text nodes that are immediate children of el.
function directText(el) {
    let text = "";
    el.childNodes.forEach((node) => {
        if (node.nodeType === Node.TEXT_NODE) {
            text += node.textContent;
        }
    });
    return text.trim().toLowerCase();
}

// ─── Hide element — only hide within dropdown boundary, never walk above it ───
function hideMenuElement(el) {
    // The element to hide is the clickable item or its immediate li wrapper.
    // We MUST NOT walk up past .o_dropdown_menu or .dropdown-menu boundary.
    const dropdownParent = el.closest(".o_dropdown_menu, .dropdown-menu");

    if (dropdownParent) {
        // We are inside a dropdown — hide the li or the element itself
        const li = el.closest("li");
        if (li && dropdownParent.contains(li)) {
            li.style.setProperty("display", "none", "important");
        } else {
            el.style.setProperty("display", "none", "important");
        }
    } else {
        // Flat menu (like .o_menu_sections nav items) — hide the anchor/span only
        el.style.setProperty("display", "none", "important");
    }
}

// ─── Apply menu restrictions ──────────────────────────────────────────────────
function applyMenus(r) {
    if (!r) return;

    // PASS 1: Match by data-menu-xmlid (most reliable, zero false positives)
    document.querySelectorAll("[data-menu-xmlid]").forEach((el) => {
        const xmlid = el.getAttribute("data-menu-xmlid") || "";
        for (const rule of XMLID_RULES) {
            if (r[rule.key] && xmlid === rule.xmlid) {
                hideMenuElement(el);
                return;
            }
        }
    });

    // PASS 2: Text matching — ONLY inside dropdown menus, ONLY direct text nodes
    // This avoids ever touching top-level navbar items like "Reporting", "Operations"
    const dropdownItems = document.querySelectorAll(
        ".o_dropdown_menu a, .o_dropdown_menu li > span, .dropdown-menu a, .dropdown-menu li > span"
    );

    dropdownItems.forEach((el) => {
        // Use directText so "Operations" span (containing Scrap as child) never matches "scrap"
        const text = directText(el);
        if (!text) return;

        for (const rule of TEXT_RULES) {
            if (r[rule.key] && text === rule.match) {
                hideMenuElement(el);
                return;
            }
        }
    });

    // PASS 3: Also check .o_nav_entry items which are flat (not inside dropdown)
    // These are safe because they are leaf items by nature in Odoo 19 sidebar nav
    document.querySelectorAll(".o_nav_entry").forEach((el) => {
        const text = directText(el);
        if (!text) return;

        for (const rule of TEXT_RULES) {
            if (r[rule.key] && text === rule.match) {
                hideMenuElement(el);
                return;
            }
        }
    });
}

// ─── Apply product field restrictions ────────────────────────────────────────
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

function applyFields(r) {
    if (!r) return;

    FIELD_RULES.forEach(({ field, key }) => {
        if (!r[key]) return;
        document.querySelectorAll(
            `.o_field_widget[name="${field}"], div[name="${field}"], td[name="${field}"]`
        ).forEach((widget) => {
            const row =
                widget.closest(".o_wrap_field") ||
                widget.closest(".o_setting_box") ||
                widget.closest("tr") ||
                widget.closest(".o_cell");
            (row || widget).style.setProperty("display", "none", "important");
        });
    });

    READONLY_RULES.forEach(({ field, key }) => {
        if (!r[key]) return;
        document.querySelectorAll(
            `.o_field_widget[name="${field}"] input, .o_field_widget[name="${field}"] .o_field_monetary input`
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
        scheduleApply(500);
        scheduleApply(1200); // second pass after full render

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
