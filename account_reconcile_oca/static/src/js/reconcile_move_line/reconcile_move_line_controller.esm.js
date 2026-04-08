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
import {useBus} from "@web/core/utils/hooks";

const {onMounted, useEffect} = owl;

export class ReconcileMoveLineController extends ListController {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this._isSorting = false;  // Guard flag to prevent infinite loop

        useBus(this.model.bus, "update", () => {
            // Skip if WE triggered this update (prevents infinite loop)
            if (this._isSorting) return;
            if (this.model?.root?.records?.length > 0) {
                this._applySmartSort();
            }
        });

        useEffect(
            () => {
                this._isSorting = false;
                const records = this.model?.root?.records;
                if (records?.length > 0) {
                    this._applySmartSort();
                }
            },
            () => [this.props.parentRecord?.resId]
        );

        onMounted(() => {
            const records = this.model?.root?.records;
            if (records?.length > 0) {
                this._applySmartSort();
            }
        });
    }

    _getStatementAmount() {
        const parentRecord = this.props.parentRecord;
        if (!parentRecord) return 0;
        const data = parentRecord.data;

        // Try direct fields first
        const candidates = [
            "amount",
            "amount_currency",
            "amount_total_signed",
            "amount_residual",
            "amount_company_currency_signed",
        ];
        for (const field of candidates) {
            if (data[field] !== undefined && data[field] !== false && data[field] !== 0) {
                return data[field];
            }
        }

        // Fallback: read from reconcile_data_info liquidity line
        const reconcileInfo = data?.reconcile_data_info;
        if (reconcileInfo?.data) {
            const liquidityLine = reconcileInfo.data.find(l => l.kind === "liquidity");
            if (liquidityLine) {
                return liquidityLine.amount;
            }
        }

        return 0;
    }

    _applySmartSort() {
        const records = this.model?.root?.records;
        if (!records || records.length === 0) return;

        const stmtAmount = this._getStatementAmount();
        if (stmtAmount === 0) return;

        const absStmt = Math.abs(stmtAmount);

        records.sort((a, b) => {
            const aRes = Math.abs(a.data?.amount_residual ?? 0);
            const bRes = Math.abs(b.data?.amount_residual ?? 0);
            return Math.abs(aRes - absStmt) - Math.abs(bRes - absStmt);
        });

        // Set guard BEFORE notify to block the re-entrant bus event
        this._isSorting = true;
        this.model.notify();
        // Reset guard after a tick so future legitimate updates still sort
        Promise.resolve().then(() => { this._isSorting = false; });
    }

    async openRecord(record) {
        const data = {};
        const displayName =
            record.data?.name ||
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