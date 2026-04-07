//import {ListController} from "@web/views/list/list_controller";
//export class ReconcileMoveLineController extends ListController {
//    async openRecord(record) {
//        var data = {};
//        const displayName = record.data?.name ||
//                            record.data?.move_id?.display_name ||
//                            String(record.resId);
//        data[this.props.parentField] = {
//            id: record.resId,
//            display_name: displayName,
//        };
//        await this.props.parentRecord.update(data);
//    }
//    async clickAddAll() {
//        await this.props.parentRecord.save();
//        await this.model.orm.call(
//            this.props.parentRecord.resModel,
//            "add_multiple_lines",
//            [this.props.parentRecord.resIds, this.model.root.domain]
//        );
//        await this.props.parentRecord.load();
//        this.props.parentRecord.model.notify();
//    }
//}
//ReconcileMoveLineController.template = `account_reconcile_oca.ReconcileMoveLineController`;
//ReconcileMoveLineController.props = {
//    ...ListController.props,
//    parentRecord: {type: Object, optional: true},
//    parentField: {type: String, optional: true},
//};
import {ListController} from "@web/views/list/list_controller";

export class ReconcileMoveLineController extends ListController {

    async openRecord(record) {
        var data = {};
        const displayName = record.data?.name ||
                            record.data?.move_id?.display_name ||
                            String(record.resId);
        data[this.props.parentField] = {
            id: record.resId,
            display_name: displayName,
        };
        await this.props.parentRecord.update(data);
    }

    async clickAddAll() {
        await this.props.parentRecord.save();
        await this.model.orm.call(
            this.props.parentRecord.resModel,
            "add_multiple_lines",
            [this.props.parentRecord.resIds, this.model.root.domain]
        );
        await this.props.parentRecord.load();
        this.props.parentRecord.model.notify();
    }

    // Sort move lines so closest amount_residual to the statement line appears first
    _sortRecordsByAmountMatch(records) {
        const parentAmount = this.props.parentRecord &&
            (this.props.parentRecord.data.amount_currency ||
             this.props.parentRecord.data.amount) || 0;
        const targetAmount = Math.abs(parentAmount);
        return [...records].sort((a, b) => {
            const aResidual = Math.abs(
                a.data.amount_residual_currency || a.data.amount_residual || 0
            );
            const bResidual = Math.abs(
                b.data.amount_residual_currency || b.data.amount_residual || 0
            );
            const aDiff = Math.abs(aResidual - targetAmount);
            const bDiff = Math.abs(bResidual - targetAmount);
            return aDiff - bDiff;
        });
    }

    get sortedRecords() {
        const records = this.model.root.records || [];
        return this._sortRecordsByAmountMatch(records);
    }
}

ReconcileMoveLineController.template =
    `account_reconcile_oca.ReconcileMoveLineController`;
ReconcileMoveLineController.props = {
    ...ListController.props,
    parentRecord: {type: Object, optional: true},
    parentField: {type: String, optional: true},
};