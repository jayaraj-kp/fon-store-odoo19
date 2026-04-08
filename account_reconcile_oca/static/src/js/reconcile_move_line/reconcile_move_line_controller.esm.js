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

const {onMounted, useEffect} = owl;

export class ReconcileMoveLineController extends ListController {
    setup() {
        super.setup();
        this.orm = useService("orm");

        useEffect(
            (parentRecord) => {
                console.log("🔄 useEffect triggered, parentRecord:", parentRecord);
                console.log("🔄 parentRecord.data:", parentRecord?.data);
                console.log("🔄 amount from parentRecord:", parentRecord?.data?.amount);
                if (parentRecord) {
                    this._applySmartSort();
                }
            },
            () => [this.props.parentRecord]
        );

        onMounted(() => {
            console.log("✅ onMounted fired");
            console.log("✅ this.props.parentRecord:", this.props.parentRecord);
            console.log("✅ this.props.parentRecord.data:", this.props.parentRecord?.data);
            console.log("✅ amount:", this.props.parentRecord?.data?.amount);
            console.log("✅ this.model:", this.model);
            console.log("✅ this.model.root:", this.model?.root);
            console.log("✅ this.model.root.records:", this.model?.root?.records);
            if (this.model?.root?.records) {
                console.log("✅ records count:", this.model.root.records.length);
                console.log("✅ first record data keys:", Object.keys(this.model.root.records[0]?.data || {}));
                console.log("✅ first record amount_residual:", this.model.root.records[0]?.data?.amount_residual);
                console.log("✅ first record amount_residual_currency:", this.model.root.records[0]?.data?.amount_residual_currency);
            }
            this._applySmartSort();
        });
    }

    _getStatementAmount() {
        const parentRecord = this.props.parentRecord;
        console.log("💰 _getStatementAmount - parentRecord:", parentRecord);
        console.log("💰 _getStatementAmount - data:", parentRecord?.data);
        // Try all possible field names
        const amount1 = parentRecord?.data?.amount;
        const amount2 = parentRecord?.data?.amount_currency;
        const amount3 = parentRecord?.data?.amount_total_signed;
        console.log("💰 amount (data.amount):", amount1);
        console.log("💰 amount_currency (data.amount_currency):", amount2);
        console.log("💰 amount_total_signed (data.amount_total_signed):", amount3);
        return amount1 ?? 0;
    }

    _applySmartSort() {
        console.log("🔀 _applySmartSort called");
        const records = this.model?.root?.records;
        console.log("🔀 records:", records);
        console.log("🔀 records length:", records?.length);

        if (!records || records.length === 0) {
            console.warn("🔀 No records to sort, returning early");
            return;
        }

        const stmtAmount = this._getStatementAmount();
        console.log("🔀 stmtAmount:", stmtAmount);

        if (stmtAmount === 0) {
            console.warn("🔀 stmtAmount is 0, returning early");
            return;
        }

        const absStmt = Math.abs(stmtAmount);
        console.log("🔀 absStmt:", absStmt);

        // Log all records before sort
        console.log("📋 BEFORE SORT:");
        records.forEach((r, i) => {
            console.log(`  [${i}] id=${r.resId} amount_residual=${r.data?.amount_residual} amount_residual_currency=${r.data?.amount_residual_currency} name=${r.data?.name}`);
        });

        records.sort((a, b) => {
            const aRes = a.data?.amount_residual ?? 0;
            const bRes = b.data?.amount_residual ?? 0;
            const aDiff = Math.abs(Math.abs(aRes) - absStmt);
            const bDiff = Math.abs(Math.abs(bRes) - absStmt);
            return aDiff - bDiff;
        });

        // Log all records after sort
        console.log("📋 AFTER SORT:");
        records.forEach((r, i) => {
            console.log(`  [${i}] id=${r.resId} amount_residual=${r.data?.amount_residual} amount_residual_currency=${r.data?.amount_residual_currency} name=${r.data?.name}`);
        });

        console.log("🔔 calling model.notify()");
        this.model.notify();
        console.log("🔔 model.notify() done");
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