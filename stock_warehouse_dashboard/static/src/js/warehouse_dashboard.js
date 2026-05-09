/** @odoo-module **/

import { KanbanController } from "@web/views/kanban/kanban_controller";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

/**
 * Patch the KanbanController to handle clicks on
 * .o_wh_badge_send and .o_wh_badge_accept elements.
 *
 * These are rendered inside the picking-type kanban cards
 * via the inherited view (stock_warehouse_dashboard_views.xml).
 */
patch(KanbanController.prototype, {
    setup() {
        super.setup(...arguments);
        this._warehouseDashboardOrm = useService("orm");
        this._warehouseDashboardAction = useService("action");
    },
});

/**
 * Delegate badge clicks at the renderer level (event delegation
 * on the kanban board container).
 */
patch(KanbanRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        this._wdOrm = useService("orm");
        this._wdAction = useService("action");
    },
});

// Global click handler (document-level delegation)
document.addEventListener("click", async function (ev) {
    const badge = ev.target.closest(".o_wh_badge_send, .o_wh_badge_accept");
    if (!badge) return;

    ev.preventDefault();
    ev.stopPropagation();

    const warehouseId = parseInt(badge.dataset.warehouseId, 10);
    const direction = badge.dataset.direction; // 'send' or 'accept'

    if (!warehouseId || !direction) return;

    // We need an ORM call — use fetch directly since we're outside OWL here
    const method = direction === "send" ? "action_open_to_send" : "action_open_to_accept";

    try {
        const response = await fetch("/web/dataset/call_kw", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: {
                    model: "stock.warehouse",
                    method: method,
                    args: [warehouseId],
                    kwargs: {},
                },
            }),
        });
        const data = await response.json();
        if (data.result) {
            // Trigger Odoo action via the global action manager
            const actionService = owl.Component.env?.services?.action;
            if (actionService) {
                actionService.doAction(data.result);
            } else {
                // Fallback: dispatch as a URL action
                window.location.href = `/web#action=${data.result.id || ""}`;
            }
        }
    } catch (e) {
        console.error("Warehouse badge click error:", e);
    }
});
