/** @odoo-module **/

/**
 * User Access & Restrictions — access_restrictions.js
 * Odoo 19 CE compatible — FIXED v3
 *
 * KEY FIXES IN THIS VERSION:
 *
 * 1. Text matching changed from EXACT (===) to INCLUDES (contains).
 *    Previous: text === rule.match  → fails for "profit & loss (bak)"
 *    Fixed:    normalized.includes(rule.match) → matches correctly
 *
 * 2. Text is normalized before matching:
 *    - " & " → " and "  (handles OCA menus using ampersand)
 *    - "(BAK)", "(OCA)" etc. stripped out
 *    - lowercased, whitespace collapsed
 *
 * 3. All TEXT_RULES keywords use "and" (not "&") for consistency.
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
    // Accounting Reports
    { xmlid: "account.action_account_report_bs",            key: "restrict_balance_sheet" },
    { xmlid: "account.menu_action_report_bs",               key: "restrict_balance_sheet" },
    { xmlid: "account.action_account_report_pl",            key: "restrict_profit_loss" },
    { xmlid: "account.menu_action_report_pl",               key: "restrict_profit_loss" },
    { xmlid: "account.action_account_report_partner_ledger",key: "restrict_partner_ledger" },
    { xmlid: "account.menu_action_report_partner_ledger",   key: "restrict_partner_ledger" },
    { xmlid: "account.action_account_general_ledger",       key: "restrict_general_ledger" },
    { xmlid: "account.menu_action_general_ledger",          key: "restrict_general_ledger" },
    { xmlid: "account.action_account_report_trial_balance", key: "restrict_trial_balance" },
    { xmlid: "account.menu_action_report_trial_balance",    key: "restrict_trial_balance" },
    { xmlid: "account.action_account_cash_flow_report",     key: "restrict_cash_flow" },
    { xmlid: "account.menu_action_cash_flow_report",        key: "restrict_cash_flow" },
    { xmlid: "account.action_account_receivable",           key: "restrict_aged_receivable" },
    { xmlid: "account.menu_action_report_aged_receivable",  key: "restrict_aged_receivable" },
    { xmlid: "account.action_account_payable",              key: "restrict_aged_payable" },
    { xmlid: "account.menu_action_report_aged_payable",     key: "restrict_aged_payable" },
    { xmlid: "account.action_account_report_tax",           key: "restrict_tax_report" },
    { xmlid: "account.menu_action_report_tax",              key: "restrict_tax_report" },
    { xmlid: "account.action_account_report_executive_summary", key: "restrict_executive_summary" },
    { xmlid: "account.menu_action_report_executive_summary",    key: "restrict_executive_summary" },
];

// ─── Menu text → restriction key (FALLBACK — dropdown leaf items only) ────────
//
// IMPORTANT: All keywords use "and" not "&".
// The normalizeText() function converts " & " → " and " before matching,
// so "Profit & Loss (BAK)" becomes "profit and loss bak" and correctly
// matches the keyword "profit and loss".
//
// Matching uses .includes() not === so suffixes like "(BAK)" don't break matching.
const TEXT_RULES = [
    // Inventory
    { match: "scrap",                     key: "restrict_scrap_menu" },
    { match: "scraps",                    key: "restrict_scrap_menu" },
    { match: "physical inventory",        key: "restrict_physical_inventory" },
    { match: "inventory adjustments",     key: "restrict_physical_inventory" },
    { match: "replenishment",             key: "restrict_replenishment" },
    { match: "inventory valuation",       key: "restrict_inventory_valuation" },
    { match: "landed costs",              key: "restrict_landed_costs" },
    // Accounting Reports
    { match: "balance sheet",             key: "restrict_balance_sheet" },
    { match: "profit and loss",           key: "restrict_profit_loss" },   // matches "Profit & Loss (BAK)" after normalize
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

// ─── Normalize menu label for consistent matching ─────────────────────────────
//
// "Profit & Loss (BAK)" → "profit and loss bak"
// "Cash Flow Statement" → "cash flow statement"
//
function normalizeText(raw) {
    return (raw || "")
        .toLowerCase()
        .replace(/\s*&\s*/g, " and ")   // & → and
        .replace(/\(.*?\)/g, " ")        // strip (BAK), (OCA) etc.
        .replace(/\s+/g, " ")            // collapse whitespace
        .trim();
}

// ─── Get DIRECT text only (not from child elements) ───────────────────────────
// textContent includes ALL descendant text, so a parent "Operations" node
// would incorrectly match "scrap" because Scrap is a child menu item.
// directText reads only text nodes that are immediate children of the element.
function directText(el) {
    let text = "";
    el.childNodes.forEach((node) => {
        if (node.nodeType === Node.TEXT_NODE) {
            text += node.textContent;
        }
    });
    return text.trim();
}

// ─── Hide element safely — never walk above dropdown boundary ─────────────────
function hideMenuElement(el) {
    const dropdownParent = el.closest(".o_dropdown_menu, .dropdown-menu");
    if (dropdownParent) {
        const li = el.closest("li");
        if (li && dropdownParent.contains(li)) {
            li.style.setProperty("display", "none", "important");
        } else {
            el.style.setProperty("display", "none", "important");
        }
    } else {
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

    // PASS 2: Text matching — ONLY inside dropdown menus, ONLY direct text nodes.
    // Uses normalizeText() + includes() so "Profit & Loss (BAK)" matches "profit and loss".
    const dropdownItems = document.querySelectorAll(
        ".o_dropdown_menu a, .o_dropdown_menu li > span, .dropdown-menu a, .dropdown-menu li > span"
    );

    dropdownItems.forEach((el) => {
        const raw = directText(el);
        if (!raw) return;
        const normalized = normalizeText(raw);

        for (const rule of TEXT_RULES) {
            if (r[rule.key] && normalized.includes(rule.match)) {
                hideMenuElement(el);
                return;
            }
        }
    });

    // PASS 3: Flat .o_nav_entry items (sidebar leaf items in Odoo 19)
    document.querySelectorAll(".o_nav_entry").forEach((el) => {
        const raw = directText(el);
        if (!raw) return;
        const normalized = normalizeText(raw);

        for (const rule of TEXT_RULES) {
            if (r[rule.key] && normalized.includes(rule.match)) {
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