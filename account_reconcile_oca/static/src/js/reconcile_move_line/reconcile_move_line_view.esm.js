import {registry} from "@web/core/registry";
import {listView} from "@web/views/list/list_view";
import {ReconcileMoveLineController} from "./reconcile_move_line_controller.esm";
import {ReconcileMoveLineRenderer} from "./reconcile_move_line_renderer.esm";

export const ReconcileMoveLineView = {
    ...listView,
    Controller: ReconcileMoveLineController,
    Renderer: ReconcileMoveLineRenderer,
};

registry.category("views").add("reconcile_move_line", ReconcileMoveLineView);
