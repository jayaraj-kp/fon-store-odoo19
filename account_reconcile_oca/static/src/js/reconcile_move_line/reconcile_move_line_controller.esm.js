import {ListController} from "@web/views/list/list_controller";

const {onMounted} = owl;

export class ReconcileMoveLineController extends ListController {
    setup() {
        super.setup();
        onMounted(() => {
            this._applySmartSort();
        });
    }

    _applySmartSort() {
        const parentRecord = this.props.parentRecord;
        if (!parentRecord) return;
        const amount = parentRecord.data?.amount || 0;
        if (amount === 0) return;

        const records = this.model.root.records;
        if (!records || records.length === 0) return;

        // Sort records in place
        records.sort((a, b) => {
            const aVal = a.data.amount_residual_currency || 0;
            const bVal = b.data.amount_residual_currency || 0;
            const aDiff = Math.abs(Math.abs(aVal) - Math.abs(amount));
            const bDiff = Math.abs(Math.abs(bVal) - Math.abs(amount));
            // Closest amount match first
            if (aDiff !== bDiff) return aDiff - bDiff;
            // Then same sign as statement amount first
            const aSign = amount > 0 ? aVal > 0 : aVal < 0;
            const bSign = amount > 0 ? bVal > 0 : bVal < 0;
            if (aSign && !bSign) return -1;
            if (!aSign && bSign) return 1;
            return 0;
        });

        // Force re-render
        this.model.notify();
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
