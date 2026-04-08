//import {ListController} from "@web/views/list/list_controller";
//
//const {onMounted} = owl;
//
//export class ReconcileMoveLineController extends ListController {
//    setup() {
//        super.setup();
//        onMounted(() => {
//            this._applySmartSort();
//        });
//    }
//
//    _applySmartSort() {
//        const parentRecord = this.props.parentRecord;
//        if (!parentRecord) return;
//        const amount = parentRecord.data?.amount || 0;
//        if (amount === 0) return;
//
//        const records = this.model.root.records;
//        if (!records || records.length === 0) return;
//
//        // Sort records in place
//        records.sort((a, b) => {
//            const aVal = a.data.amount_residual_currency || 0;
//            const bVal = b.data.amount_residual_currency || 0;
//            const aDiff = Math.abs(Math.abs(aVal) - Math.abs(amount));
//            const bDiff = Math.abs(Math.abs(bVal) - Math.abs(amount));
//            // Closest amount match first
//            if (aDiff !== bDiff) return aDiff - bDiff;
//            // Then same sign as statement amount first
//            const aSign = amount > 0 ? aVal > 0 : aVal < 0;
//            const bSign = amount > 0 ? bVal > 0 : bVal < 0;
//            if (aSign && !bSign) return -1;
//            if (!aSign && bSign) return 1;
//            return 0;
//        });
//
//        // Force re-render
//        this.model.notify();
//    }
//
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
//
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
//
//ReconcileMoveLineController.template = `account_reconcile_oca.ReconcileMoveLineController`;
//ReconcileMoveLineController.props = {
//    ...ListController.props,
//    parentRecord: {type: Object, optional: true},
//    parentField: {type: String, optional: true},
//};
import {ListController} from "@web/views/list/list_controller";
import {useService} from "@web/core/utils/hooks";

const {onMounted, onWillUpdateProps} = owl;

export class ReconcileMoveLineController extends ListController {
    setup() {
        super.setup();
        this.orm = useService("orm");
        onMounted(async () => {
            await this._applySmartSort();
        });
        // Re-sort whenever the parent record changes (user clicks a different statement line)
        onWillUpdateProps(async () => {
            await this._applySmartSort();
        });
    }

    async _applySmartSort() {
        const parentRecord = this.props.parentRecord;
        if (!parentRecord) return;

        const statementId = parentRecord.resId;
        if (!statementId) return;

        const records = this.model.root.records;
        if (!records || records.length === 0) return;

        const amount = parentRecord.data?.amount || 0;
        if (amount === 0) return;

        try {
            // Ask the server for IDs sorted by closest-amount-match
            const sortedIds = await this.orm.call(
                "account.bank.statement.line",
                "get_move_lines_sorted_by_amount",
                [[statementId], this.model.root.domain]
            );

            if (!sortedIds || sortedIds.length === 0) return;

            // Build an index map: id → position
            const orderMap = {};
            sortedIds.forEach((id, idx) => { orderMap[id] = idx; });

            // Sort the already-loaded records using that map
            records.sort((a, b) => {
                const aPos = orderMap[a.resId] ?? 9999;
                const bPos = orderMap[b.resId] ?? 9999;
                return aPos - bPos;
            });

            this.model.notify();
        } catch (e) {
            // Graceful degradation — if RPC fails, keep default order
            console.warn("Smart sort failed:", e);
        }
    }

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
}

ReconcileMoveLineController.template = `account_reconcile_oca.ReconcileMoveLineController`;
ReconcileMoveLineController.props = {
    ...ListController.props,
    parentRecord: {type: Object, optional: true},
    parentField: {type: String, optional: true},
};