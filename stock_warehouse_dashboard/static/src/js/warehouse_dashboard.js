/** @odoo-module **/

/**
 * Stock Warehouse Dashboard – To Send / To Accept
 * Odoo 19 CE compatible
 *
 * Uses plain fetch + document-level click delegation.
 * No OWL patching required — badges are rendered server-side
 * via the inherited kanban view XML.
 */

// Odoo 19 uses /web/dataset/call_kw for RPC
async function callKw(model, method, args) {
    const response = await fetch('/web/dataset/call_kw', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
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
        console.error('RPC error:', data.error);
        return null;
    }
    return data.result;
}

// Document-level click delegation for badge buttons
document.addEventListener('click', async function (ev) {
    const badge = ev.target.closest('.o_wh_badge_send, .o_wh_badge_accept');
    if (!badge) return;

    ev.preventDefault();
    ev.stopPropagation();

    const warehouseId = parseInt(badge.dataset.warehouseId, 10);
    const direction = badge.dataset.direction; // 'send' or 'accept'

    if (!warehouseId || !direction) return;

    const method = direction === 'send'
        ? 'action_open_to_send'
        : 'action_open_to_accept';

    try {
        const action = await callKw('stock.warehouse', method, [[warehouseId]]);
        if (action) {
            // Use Odoo 19's action service via the global __owl__ registry
            const env = owl.__apps__?.[0]?.env;
            if (env?.services?.action) {
                env.services.action.doAction(action);
            } else {
                // Safe fallback: navigate via hash
                window.location.href = '/odoo/inventory';
            }
        }
    } catch (e) {
        console.error('WH Dashboard badge error:', e);
    }
});
