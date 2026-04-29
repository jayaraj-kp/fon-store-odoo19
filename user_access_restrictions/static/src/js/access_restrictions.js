/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { onWillStart } from "@odoo/owl";

// ─── Global restriction cache ────────────────────────────────────────────────
let _userRestrictions = null;

async function loadUserRestrictions(rpc) {
    if (_userRestrictions !== null) return _userRestrictions;
    try {
        _userRestrictions = await rpc("/web/dataset/call_kw", {
            model: "res.users",
            method: "get_current_user_restrictions",
            args: [],
            kwargs: {},
        });
    } catch (e) {
        console.warn("[UserRestrictions] Could not load restrictions:", e);
        _userRestrictions = {};
    }
    return _userRestrictions;
}

// ─── System Parameter Service extension ──────────────────────────────────────
// Inject restriction context into every action context so views can read it.

const restrictionService = {
    name: "user_access_restrictions",
    dependencies: ["rpc", "action"],
    async start(env, { rpc, action }) {
        const restrictions = await loadUserRestrictions(rpc);

        // Patch action manager to inject context
        const originalDoAction = action.doAction.bind(action);
        action.doAction = async (actionRequest, options = {}) => {
            if (actionRequest && typeof actionRequest === "object") {
                actionRequest.context = {
                    ...(actionRequest.context || {}),
                    ...restrictions,
                };
            }
            return originalDoAction(actionRequest, options);
        };

        return { restrictions };
    },
};

registry.category("services").add("user_access_restrictions", restrictionService);

// ─── Menu item hiding ─────────────────────────────────────────────────────────

/**
 * Maps menu name substrings (lowercase) → restriction field name.
 * If the restriction flag is true the menu item is hidden.
 */
const MENU_RESTRICTION_MAP = {
    // Inventory menus
    "scrap": "restrict_scrap_menu",
    "physical inventory": "restrict_physical_inventory",
    "inventory adjustments": "restrict_physical_inventory",
    "replenishment": "restrict_replenishment",
    "inventory valuation": "restrict_inventory_valuation",
    "landed costs": "restrict_landed_costs",

    // Accounting report menus
    "balance sheet": "restrict_balance_sheet",
    "profit & loss": "restrict_profit_loss",
    "profit and loss": "restrict_profit_loss",
    "partner ledger": "restrict_partner_ledger",
    "general ledger": "restrict_general_ledger",
    "trial balance": "restrict_trial_balance",
    "cash flow": "restrict_cash_flow",
    "aged receivable": "restrict_aged_receivable",
    "aged payable": "restrict_aged_payable",
    "tax report": "restrict_tax_report",
    "executive summary": "restrict_executive_summary",
};

/**
 * Hides menu items based on user restrictions.
 * Called after the menu is rendered.
 */
async function applyMenuRestrictions(rpc) {
    const restrictions = await loadUserRestrictions(rpc);
    if (!restrictions || Object.keys(restrictions).length === 0) return;

    // Query all menu items in the DOM
    const menuItems = document.querySelectorAll(
        ".o_menu_sections .o_nav_entry, " +
        ".o_menu_sections .o_dropdown_item, " +
        ".o_main_navbar .o_menu_brand, " +
        "[role='menuitem'], " +
        ".o_dropdown .o_dropdown_item"
    );

    menuItems.forEach((el) => {
        const label = (el.textContent || "").trim().toLowerCase();
        for (const [keyword, restrictionKey] of Object.entries(MENU_RESTRICTION_MAP)) {
            if (label.includes(keyword) && restrictions[restrictionKey]) {
                el.style.display = "none";
                el.setAttribute("data-restricted", "true");
                break;
            }
        }
    });
}

// ─── Hook into the menu rendering ────────────────────────────────────────────

const menuServiceExtension = {
    name: "user_restrictions_menu_patch",
    dependencies: ["rpc", "menu"],
    start(env, { rpc, menu }) {
        // Apply after menu loads
        const applyAfterRender = () => {
            setTimeout(() => applyMenuRestrictions(rpc), 300);
        };

        // Watch for menu changes (SPA navigation)
        const observer = new MutationObserver((mutations) => {
            const relevant = mutations.some((m) =>
                m.target &&
                (m.target.classList?.contains("o_menu_sections") ||
                 m.target.classList?.contains("o_main_navbar"))
            );
            if (relevant) applyMenuRestrictions(rpc);
        });

        // Start observing once DOM is ready
        const startObserver = () => {
            const navbar = document.querySelector(".o_main_navbar");
            if (navbar) {
                observer.observe(navbar, { childList: true, subtree: true });
                applyMenuRestrictions(rpc);
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

registry.category("services").add("user_restrictions_menu_patch", menuServiceExtension);

// ─── Product form field hiding ────────────────────────────────────────────────

/**
 * After product form renders, hide restricted fields at DOM level.
 * The Python ORM layer is the source of truth; this is a UX improvement.
 */
function applyProductFormRestrictions(restrictions) {
    if (!restrictions) return;

    const fieldMap = {
        "standard_price": "restrict_cost_price",
        "list_price": "restrict_sales_price",
        "barcode": "restrict_barcode",
        "default_code": "restrict_internal_reference",
        "taxes_id": "restrict_taxes",
        "supplier_taxes_id": "restrict_taxes",
    };

    for (const [fieldName, restrictionKey] of Object.entries(fieldMap)) {
        if (restrictions[restrictionKey]) {
            // Hide field row
            const fieldEls = document.querySelectorAll(
                `[name="${fieldName}"], .o_field_widget[name="${fieldName}"]`
            );
            fieldEls.forEach((el) => {
                const row = el.closest(".o_field_widget") || el.closest("td") || el;
                const wrapper = row.closest(".o_wrap_field") ||
                                row.closest("tr") ||
                                row.parentElement;
                if (wrapper) wrapper.style.display = "none";
            });
        }
    }
}

// Apply on URL/view change (SPA)
let _lastUrl = "";
setInterval(async () => {
    if (window.location.href !== _lastUrl) {
        _lastUrl = window.location.href;
        if (window.location.href.includes("product.template") ||
            window.location.href.includes("product.product")) {
            // Small delay to let form render
            setTimeout(async () => {
                const restrictions = _userRestrictions;
                if (restrictions) applyProductFormRestrictions(restrictions);
            }, 500);
        }
    }
}, 300);
