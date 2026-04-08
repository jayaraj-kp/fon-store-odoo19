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
        this._sortDone = false;

        // Listen to model bus — fires when records finish loading
        useBus(this.model.bus, "update", () => {
            console.log("🚌 model.bus 'update' fired");
            console.log("🚌 records length now:", this.model?.root?.records?.length);
            if (this.model?.root?.records?.length > 0) {
                this._applySmartSort();
            }
        });

        useEffect(
            (parentRecord) => {
                console.log("🔄 useEffect - parentRecord changed");
                // Reset sort flag when parent changes (new statement line selected)
                this._sortDone = false;
                const records = this.model?.root?.records;
                console.log("🔄 records length at useEffect:", records?.length);
                if (records?.length > 0) {
                    this._applySmartSort();
                }
            },
            () => [this.props.parentRecord?.resId]
        );

        onMounted(() => {
            console.log("✅ onMounted fired");
            const records = this.model?.root?.records;
            console.log("✅ records length at onMounted:", records?.length);
        });
    }

    _getStatementAmount() {
        const parentRecord = this.props.parentRecord;
        if (!parentRecord) return 0;

        // Log ALL data fields to find the amount field
        const data = parentRecord.data;
        console.log("💰 ALL parentRecord.data fields:", JSON.stringify(
            Object.fromEntries(
                Object.entries(data).filter(([k, v]) =>
                    typeof v === "number" || (typeof v === "string" && !isNaN(v))
                )
            )
        ));

        // Try every possible amount field
        const candidates = [
            "amount",
            "amount_currency",
            "amount_total_signed",
            "amount_residual",
            "amount_company_currency_signed",
        ];
        for (const field of candidates) {
            if (data[field] !== undefined && data[field] !== false) {
                console.log(`💰 Found amount in field '${field}':`, data[field]);
                return data[field];
            }
        }

        // Fallback: get from reconcile_data_info liquidity line
        const reconcileInfo = data?.reconcile_data_info;
        if (reconcileInfo?.data) {
            const liquidityLine = reconcileInfo.data.find(l => l.kind === "liquidity");
            if (liquidityLine) {
                console.log("💰 Got amount from reconcile_data_info liquidity line:", liquidityLine.amount);
                return liquidityLine.amount;
            }
        }

        console.warn("💰 Could not find amount field!");
        return 0;
    }

    _applySmartSort() {
        const records = this.model?.root?.records;
        if (!records || records.length === 0) {
            console.warn("🔀 No records, skipping sort");
            return;
        }

        const stmtAmount = this._getStatementAmount();
        console.log("🔀 stmtAmount:", stmtAmount);

        if (stmtAmount === 0) {
            console.warn("🔀 stmtAmount is 0, skipping sort");
            return;
        }

        const absStmt = Math.abs(stmtAmount);

        console.log("📋 BEFORE SORT (first 5):");
        records.slice(0, 5).forEach((r, i) => {
            console.log(`  [${i}] id=${r.resId} residual=${r.data?.amount_residual} residual_cur=${r.data?.amount_residual_currency}`);
        });

        records.sort((a, b) => {
            const aRes = Math.abs(a.data?.amount_residual ?? 0);
            const bRes = Math.abs(b.data?.amount_residual ?? 0);
            const aDiff = Math.abs(aRes - absStmt);
            const bDiff = Math.abs(bRes - absStmt);
            return aDiff - bDiff;
        });

        console.log("📋 AFTER SORT (first 5):");
        records.slice(0, 5).forEach((r, i) => {
            console.log(`  [${i}] id=${r.resId} residual=${r.data?.amount_residual} residual_cur=${r.data?.amount_residual_currency}`);
        });

        this.model.notify();
        console.log("✅ Sort applied and model notified");
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