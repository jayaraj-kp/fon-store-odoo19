//import {KanbanRecord} from "@web/views/kanban/kanban_record";
//
//export class ReconcileKanbanRecord extends KanbanRecord {
//    getRecordClasses() {
//        var result = super.getRecordClasses();
//        if (this.props.selectedRecordId === this.props.record.resId) {
//            result += " o_kanban_record_reconcile_oca_selected";
//        }
//        return result;
//    }
//}
//ReconcileKanbanRecord.props = [...KanbanRecord.props, "selectedRecordId?"];
import {KanbanRecord} from "@web/views/kanban/kanban_record";

export class ReconcileKanbanRecord extends KanbanRecord {
    getRecordClasses() {
        var result = super.getRecordClasses();
        // Use == instead of === to handle number/string type mismatch
        if (this.props.selectedRecordId == this.props.record.resId) {
            result += " o_kanban_record_reconcile_oca_selected";
        }
        return result;
    }
}
ReconcileKanbanRecord.props = [...KanbanRecord.props, "selectedRecordId?"];