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
//    // Now using picking_type_id (not warehouse_id)
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
//        // Call on stock.picking.type with the correct record id
//        const action = await callKw('stock.picking.type', method, [[pickingTypeId]]);
//        if (action) {
//            const env = owl.__apps__?.[0]?.env;
//            if (env?.services?.action) {
//                env.services.action.doAction(action);
//            } else {
//                console.warn('WH Dashboard: action service not found, falling back');
//                window.location.href = '/odoo/inventory/transfers';
//            }
//        }
//    } catch (e) {
//        console.error('WH Dashboard badge click error:', e);
//    }
//});
/** @odoo-module **/

/**
 * Stock Warehouse Dashboard – To Send / To Accept
 * Odoo 19 CE
 *
 * Calls action_open_to_send / action_open_to_accept on stock.picking.type
 * using the picking_type_id from the kanban card (data-picking-type-id).
 */

async function callKw(model, method, args) {
    const response = await fetch('/web/dataset/call_kw', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            jsonrpc: '2.0',
            id: Math.floor(Math.random() * 100000),
            method: 'call',
            params: {
                model: model,
                method: method,
                args: args,
                kwargs: { context: {} },
            },
        }),
    });
    const data = await response.json();
    if (data.error) {
        console.error('WH Dashboard RPC error:', data.error);
        return null;
    }
    return data.result;
}

document.addEventListener('click', async function (ev) {
    const badge = ev.target.closest('.o_wh_badge_send, .o_wh_badge_accept');
    if (!badge) return;

    ev.preventDefault();
    ev.stopPropagation();

    const pickingTypeId = parseInt(badge.dataset.pickingTypeId, 10);
    const direction = badge.dataset.direction; // 'send' or 'accept'

    if (!pickingTypeId || !direction) {
        console.warn('WH Dashboard: missing pickingTypeId or direction', badge.dataset);
        return;
    }

    const method = direction === 'send'
        ? 'action_open_to_send'
        : 'action_open_to_accept';

    try {
        const action = await callKw('stock.picking.type', method, [[pickingTypeId]]);
        if (action) {
            // Odoo 19: access action service via __WOWL_DEBUG__.root.env
            const env = window.odoo?.__WOWL_DEBUG__?.root?.env;
            if (env?.services?.action) {
                env.services.action.doAction(action);
            } else {
                console.warn('WH Dashboard: action service not found');
            }
        }
    } catch (e) {
        console.error('WH Dashboard badge click error:', e);
    }
});