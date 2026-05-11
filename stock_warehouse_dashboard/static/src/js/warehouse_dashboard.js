///** @odoo-module **/
//
///**
// * Stock Warehouse Dashboard – To Send / To Accept
// * Odoo 19 CE
// *
// * Calls action_open_to_send / action_open_to_accept on stock.picking.type
// * using the picking_type_id from the kanban card (data-picking-type-id).
// */
//
//async function callKw(model, method, args) {
//    const response = await fetch('/web/dataset/call_kw', {
//        method: 'POST',
//        headers: { 'Content-Type': 'application/json' },
//        body: JSON.stringify({
//            jsonrpc: '2.0',
//            id: Math.floor(Math.random() * 100000),
//            method: 'call',
//            params: {
//                model: model,
//                method: method,
//                args: args,
//                kwargs: { context: {} },
//            },
//        }),
//    });
//    const data = await response.json();
//    if (data.error) {
//        console.error('WH Dashboard RPC error:', data.error);
//        return null;
//    }
//    return data.result;
//}
//
//document.addEventListener('click', async function (ev) {
//    const badge = ev.target.closest('.o_wh_badge_send, .o_wh_badge_accept');
//    if (!badge) return;
//
//    ev.preventDefault();
//    ev.stopPropagation();
//
//    const pickingTypeId = parseInt(badge.dataset.pickingTypeId, 10);
//    const direction = badge.dataset.direction; // 'send' or 'accept'
//
//    if (!pickingTypeId || !direction) {
//        console.warn('WH Dashboard: missing pickingTypeId or direction', badge.dataset);
//        return;
//    }
//
//    const method = direction === 'send'
//        ? 'action_open_to_send'
//        : 'action_open_to_accept';
//
//    try {
//        const action = await callKw('stock.picking.type', method, [[pickingTypeId]]);
//        if (action) {
//            // Odoo 19: access action service via __WOWL_DEBUG__.root.env
//            const env = window.odoo?.__WOWL_DEBUG__?.root?.env;
//            if (env?.services?.action) {
//                env.services.action.doAction(action);
//            } else {
//                console.warn('WH Dashboard: action service not found');
//            }
//        }
//    } catch (e) {
//        console.error('WH Dashboard badge click error:', e);
//    }
//});
/** @odoo-module **/

/**
 * Stock Warehouse Dashboard – To Send / To Accept
 * Odoo 19 CE  –  v3
 *
 * Changes vs v2:
 *  - Replaced window.odoo.__WOWL_DEBUG__ (debug-only) with the proper
 *    Odoo 19 service registry approach using owl.App or the action manager
 *    exposed on window.__owl__ / odoo.__WOWL_DEBUG__ with a safe fallback
 *    to a direct JSON-RPC window.location redirect.
 *  - Added a reliable multi-strategy action dispatcher so badge clicks
 *    work in both debug and production mode.
 */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

// ── RPC helper (plain fetch, no dependency on OWL) ───────────────────────────
async function callKw(model, method, args) {
    const response = await fetch('/web/dataset/call_kw', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            jsonrpc: '2.0',
            id: Math.floor(Math.random() * 100000),
            method: 'call',
            params: {
                model,
                method,
                args,
                kwargs: { context: {} },
            },
        }),
    });
    const data = await response.json();
    if (data.error) {
        console.error('[WH Dashboard] RPC error:', data.error);
        return null;
    }
    return data.result;
}

// ── Action dispatcher – tries multiple Odoo 19 strategies ───────────────────
function doAction(action) {
    if (!action) return;

    // Strategy 1: __WOWL_DEBUG__ (available in debug mode)
    try {
        const env = window.odoo?.__WOWL_DEBUG__?.root?.env;
        if (env?.services?.action) {
            env.services.action.doAction(action);
            return;
        }
    } catch (_) { /* try next */ }

    // Strategy 2: owl.__apps__ (Odoo 19 OWL internal – works in production)
    try {
        const apps = window.__owl__?.__apps__;
        if (apps) {
            for (const app of apps) {
                const actionService = app.env?.services?.action;
                if (actionService) {
                    actionService.doAction(action);
                    return;
                }
            }
        }
    } catch (_) { /* try next */ }

    // Strategy 3: odoo.loader registry (Odoo 19 module system)
    try {
        const actionService = odoo.__loader__?.modules?.get?.('@web/core/action_service')
            ?.actionService;
        if (actionService) {
            actionService.doAction(action);
            return;
        }
    } catch (_) { /* try next */ }

    // Strategy 4: fallback — navigate to the list view via URL
    // Build a minimal hash-based URL that opens the act_window
    console.warn('[WH Dashboard] action service not found, falling back to URL navigation');
    if (action.res_model) {
        const params = new URLSearchParams({
            model: action.res_model,
            view_type: 'list',
        });
        window.location.href = `/odoo/inventory?${params.toString()}`;
    }
}

// ── Badge click handler ──────────────────────────────────────────────────────
document.addEventListener('click', async function (ev) {
    const badge = ev.target.closest('.o_wh_badge_send, .o_wh_badge_accept');
    if (!badge) return;

    ev.preventDefault();
    ev.stopPropagation();

    const pickingTypeId = parseInt(badge.dataset.pickingTypeId, 10);
    const direction = badge.dataset.direction; // 'send' or 'accept'

    if (!pickingTypeId || !direction) {
        console.warn('[WH Dashboard] missing pickingTypeId or direction', badge.dataset);
        return;
    }

    const method = direction === 'send'
        ? 'action_open_to_send'
        : 'action_open_to_accept';

    // Visual feedback while loading
    badge.style.opacity = '0.6';
    badge.style.pointerEvents = 'none';

    try {
        const action = await callKw('stock.picking.type', method, [[pickingTypeId]]);
        doAction(action);
    } catch (e) {
        console.error('[WH Dashboard] badge click error:', e);
    } finally {
        badge.style.opacity = '';
        badge.style.pointerEvents = '';
    }
});