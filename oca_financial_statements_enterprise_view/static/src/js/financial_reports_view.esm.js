///** @odoo-module **/
///**
// * OCA Financial Statements — Enterprise Interactive View
// * Balance Sheet & Profit and Loss with Enterprise-style layout.
// */
//
//import {
//    Component,
//    useState,
//    onWillStart,
//    onMounted,
//    onWillUnmount,
//    useRef,
//} from "@odoo/owl";
//import { useService } from "@web/core/utils/hooks";
//import { rpc } from "@web/core/network/rpc";
//import { registry } from "@web/core/registry";
//
//function fmtAmt(value, decimals = 2) {
//    if (value === null || value === undefined) return "0.00";
//    return Number(value).toLocaleString(undefined, {
//        minimumFractionDigits: decimals,
//        maximumFractionDigits: decimals,
//    });
//}
//
//function defaultDateFrom() {
//    const d = new Date();
//    return `${d.getFullYear()}-01-01`;
//}
//
//function defaultDateTo() {
//    return new Date().toISOString().slice(0, 10);
//}
//
//function displayDate(isoStr) {
//    if (!isoStr) return "";
//    const [y, m, d] = isoStr.split("-");
//    return `${d}/${m}/${y}`;
//}
//
//function isoDate(d) {
//    return d.toISOString().slice(0, 10);
//}
//
//function subtractDays(isoStr, days) {
//    const d = new Date(isoStr);
//    d.setDate(d.getDate() - days);
//    return isoDate(d);
//}
//
//function subtractMonths(isoStr, months) {
//    const d = new Date(isoStr);
//    d.setMonth(d.getMonth() - months);
//    return isoDate(d);
//}
//
//function subtractYears(isoStr, years) {
//    const d = new Date(isoStr);
//    d.setFullYear(d.getFullYear() - years);
//    return isoDate(d);
//}
//
//function periodLengthDays(dateFrom, dateTo) {
//    const dFrom = new Date(dateFrom);
//    const dTo = new Date(dateTo);
//    return Math.ceil(Math.abs(dTo - dFrom) / (1000 * 60 * 60 * 24)) + 1;
//}
//
//export class FinancialStatementsView extends Component {
//    static template = "oca_fs.FinancialStatementsView";
//    static props = ["*"];
//
//    setup() {
//        this.action = useService("action");
//        this.notification = useService("notification");
//
//        const reportType =
//            this.props.action?.params?.default_report_type || "bs";
//
//        this.state = useState({
//            reportType,
//            lines: [],
//            currencyName: "",
//            currencySymbol: "",
//            companyName: "",
//            companyId: null,
//            loading: false,
//            error: null,
//            exportingPdf: false,
//
//            dateFrom: defaultDateFrom(),
//            dateTo: defaultDateTo(),
//            targetMove: "posted",
//
//            collapsedSections: new Set(),
//            showUnpostedWarning: true,
//            hasUnposted: false,
//
//            comparisonMode: "none",
//            comparisonPeriodCount: 1,
//            comparisonDateFrom: defaultDateFrom(),
//            comparisonDateTo: defaultDateTo(),
//            comparisonFormat: "absolute",
//            periodOrder: "desc",
//            percentageOfLineId: null,
//            percentageOfLineName: "",
//            percentageOfPickerOpen: false,
//            comparisonColumns: [],
//
//            comparisonDropdownOpen: false,
//            optionsDropdownOpen: false,
//        });
//
//        this.comparisonDropdownRef = useRef("comparisonDropdownRef");
//        this.optionsDropdownRef = useRef("optionsDropdownRef");
//
//        onWillStart(async () => {
//            await this._loadInitData();
//            await this._loadData();
//        });
//
//        this._docClickHandler = this._onDocClick.bind(this);
//        onMounted(() => {
//            document.addEventListener("click", this._docClickHandler);
//        });
//        onWillUnmount(() => {
//            document.removeEventListener("click", this._docClickHandler);
//        });
//    }
//
//    _onDocClick(ev) {
//        if (this.state.comparisonDropdownOpen) {
//            const el = this.comparisonDropdownRef.el;
//            if (el && !el.contains(ev.target)) {
//                this.state.comparisonDropdownOpen = false;
//                this.state.percentageOfPickerOpen = false;
//            }
//        }
//        if (this.state.optionsDropdownOpen) {
//            const el = this.optionsDropdownRef.el;
//            if (el && !el.contains(ev.target)) {
//                this.state.optionsDropdownOpen = false;
//            }
//        }
//    }
//
//    async _loadInitData() {
//        try {
//            const result = await rpc("/oca_fs/init", {
//                company_id: this.state.companyId,
//            });
//            this.state.companyId = result.company_id;
//            this.state.companyName = result.company_name;
//            this.state.currencyName = result.currency_name;
//            this.state.currencySymbol = result.currency_symbol;
//            if (result.date_from) this.state.dateFrom = result.date_from;
//            if (result.date_to) this.state.dateTo = result.date_to;
//        } catch (e) {
//            console.error("FS init error:", e);
//        }
//    }
//
//    async _loadData() {
//        this.state.loading = true;
//        this.state.error = null;
//        try {
//            const compPeriods = this.getComparisonPeriods();
//            const payload = {
//                report_type: this.state.reportType,
//                date_from: this.state.dateFrom,
//                date_to: this.state.dateTo,
//                company_id: this.state.companyId,
//                target_move: this.state.targetMove,
//                comparison_mode: this.state.comparisonMode,
//            };
//            if (
//                compPeriods &&
//                compPeriods.length &&
//                this.state.comparisonMode !== "percentage_of"
//            ) {
//                payload.comparison_periods = compPeriods;
//            }
//            const result = await rpc("/oca_fs/get_data", payload);
//            this.state.lines = result.lines || [];
//            this.state.comparisonColumns = result.comparison_columns || [];
//            this.state.currencyName = result.currency_name || this.state.currencyName;
//            this.state.currencySymbol =
//                result.currency_symbol || this.state.currencySymbol;
//            this.state.companyName = result.company_name || this.state.companyName;
//            this.state.hasUnposted = result.has_unposted || false;
//        } catch (e) {
//            console.error("FS data error:", e);
//            this.state.error =
//                "Failed to load report data. Please check the console for details.";
//        } finally {
//            this.state.loading = false;
//        }
//    }
//
//    get reportTitle() {
//        return this.state.reportType === "bs" ? "Balance Sheet" : "Profit and Loss";
//    }
//
//    get isBalanceSheet() {
//        return this.state.reportType === "bs";
//    }
//
//    get showComparison() {
//        return (
//            this.state.comparisonMode !== "none" &&
//            this.state.comparisonMode !== "percentage_of" &&
//            this.orderedComparisonColumns.length > 0
//        );
//    }
//
//    get showPercentageOf() {
//        return (
//            this.state.comparisonMode === "percentage_of" &&
//            !!this.state.percentageOfLineId
//        );
//    }
//
//    get orderedComparisonColumns() {
//        const cols = [...(this.state.comparisonColumns || [])];
//        if (this.state.periodOrder === "asc") {
//            cols.reverse();
//        }
//        return cols;
//    }
//
//    get dateFilterLabel() {
//        if (this.isBalanceSheet) {
//            return `As of ${displayDate(this.state.dateTo)}`;
//        }
//        const year = (this.state.dateTo || "").slice(0, 4);
//        if (year) return year;
//        return displayDate(this.state.dateFrom);
//    }
//
//    get optionsDropdownLabel() {
//        return this.state.targetMove === "posted"
//            ? "Posted Entries, Accrual Basis"
//            : "Draft & Posted Entries, Accrual Basis";
//    }
//
//    get comparisonModeLabel() {
//        if (this.state.comparisonMode === "none") return "Comparison";
//        if (this.state.comparisonMode === "previous_period") {
//            const n = this.state.comparisonPeriodCount;
//            return n > 1 ? `Previous Period (${n})` : "Previous Period";
//        }
//        if (this.state.comparisonMode === "same_period_last_year") {
//            const n = this.state.comparisonPeriodCount;
//            return n > 1 ? `Same Period Last Year (${n})` : "Same Period Last Year";
//        }
//        if (this.state.comparisonMode === "percentage_of") {
//            return this.state.percentageOfLineName
//                ? `Comparison: ${this.state.percentageOfLineName}`
//                : "Percentage of";
//        }
//        return "Specific Date";
//    }
//
//    getComparisonPeriods() {
//        if (
//            this.state.comparisonMode === "none" ||
//            this.state.comparisonMode === "percentage_of"
//        ) {
//            return null;
//        }
//
//        const count = Math.max(1, Math.min(12, this.state.comparisonPeriodCount || 1));
//        const periods = [];
//
//        if (this.state.comparisonMode === "previous_period") {
//            if (this.isBalanceSheet) {
//                for (let i = 1; i <= count; i++) {
//                    const compTo = subtractMonths(this.state.dateTo, i);
//                    periods.push({
//                        date_from: compTo,
//                        date_to: compTo,
//                        label: displayDate(compTo),
//                    });
//                }
//            } else {
//                const diffDays = periodLengthDays(
//                    this.state.dateFrom,
//                    this.state.dateTo
//                );
//                for (let i = 1; i <= count; i++) {
//                    const shift = diffDays * i;
//                    const compFrom = subtractDays(this.state.dateFrom, shift);
//                    const compTo = subtractDays(this.state.dateTo, shift);
//                    periods.push({
//                        date_from: compFrom,
//                        date_to: compTo,
//                        label: `${displayDate(compFrom)} – ${displayDate(compTo)}`,
//                    });
//                }
//            }
//        } else if (this.state.comparisonMode === "same_period_last_year") {
//            for (let i = 1; i <= count; i++) {
//                if (this.isBalanceSheet) {
//                    const compTo = subtractYears(this.state.dateTo, i);
//                    periods.push({
//                        date_from: compTo,
//                        date_to: compTo,
//                        label: displayDate(compTo),
//                    });
//                } else {
//                    const compFrom = subtractYears(this.state.dateFrom, i);
//                    const compTo = subtractYears(this.state.dateTo, i);
//                    periods.push({
//                        date_from: compFrom,
//                        date_to: compTo,
//                        label: `${displayDate(compFrom)} – ${displayDate(compTo)}`,
//                    });
//                }
//            }
//        } else if (this.state.comparisonMode === "specific_date") {
//            periods.push({
//                date_from: this.state.comparisonDateFrom,
//                date_to: this.state.comparisonDateTo,
//                label: this.isBalanceSheet
//                    ? displayDate(this.state.comparisonDateTo)
//                    : `${displayDate(this.state.comparisonDateFrom)} – ${displayDate(this.state.comparisonDateTo)}`,
//            });
//        }
//
//        return periods;
//    }
//
//    getPercentageOfLines() {
//        const result = [];
//        const walk = (lines, depth = 0) => {
//            for (const line of lines) {
//                const selectable =
//                    line.style === "header" ||
//                    line.style === "group" ||
//                    line.style === "subsection" ||
//                    line.line_type === "subtotal";
//                if (selectable) {
//                    result.push({
//                        id: line.id,
//                        name: line.name,
//                        level: depth,
//                    });
//                }
//                if (line.children?.length) {
//                    walk(line.children, depth + 1);
//                }
//            }
//        };
//        walk(this.state.lines);
//        return result;
//    }
//
//    getLineBalanceById(lineId) {
//        let found = 0;
//        const walk = (lines) => {
//            for (const line of lines) {
//                if (line.id === lineId) {
//                    found = line.balance || 0;
//                    return true;
//                }
//                if (line.children?.length && walk(line.children)) return true;
//            }
//            return false;
//        };
//        walk(this.state.lines);
//        return found;
//    }
//
//    getComparisonValue(line, compBalance) {
//        if (this.state.comparisonFormat === "percentage") {
//            const current = line.balance || 0;
//            const comp = compBalance || 0;
//            if (comp === 0) return comp === current ? 0 : null;
//            return ((current - comp) / Math.abs(comp)) * 100;
//        }
//        return compBalance || 0;
//    }
//
//    fmtComparisonValue(line, compBalance) {
//        const val = this.getComparisonValue(line, compBalance);
//        if (val === null) return "n/a";
//        if (this.state.comparisonFormat === "percentage") {
//            return `${fmtAmt(val, 1)}%`;
//        }
//        return this.fmtNumWithSym(val);
//    }
//
//    getPercentageOfValue(line) {
//        const base = this.getLineBalanceById(this.state.percentageOfLineId);
//        if (!base) return 0;
//        return ((line.balance || 0) / base) * 100;
//    }
//
//    fmtPctOf(line) {
//        return `${fmtAmt(this.getPercentageOfValue(line), 1)}%`;
//    }
//
//    pctOfClass(line) {
//        const pct = this.getPercentageOfValue(line);
//        if (pct >= 50) return "oca-fs-pct-high";
//        if (pct > 0) return "oca-fs-pct-mid";
//        return "oca-fs-pct-zero";
//    }
//
//    getComparisonBalanceForColumn(line, colIndex) {
//        const ordered = this.orderedComparisonColumns;
//        if (!ordered.length || !line.comparison_balances) {
//            return line.comparison_balance || 0;
//        }
//        const col = ordered[colIndex];
//        if (!col) return 0;
//        const match = line.comparison_balances.find(
//            (cb) => cb.label === col.label && cb.date_to === col.date_to
//        );
//        return match ? match.balance : 0;
//    }
//
//    onDateFromChange(ev) {
//        this.state.dateFrom = ev.target.value;
//        this._loadData();
//    }
//
//    onDateToChange(ev) {
//        this.state.dateTo = ev.target.value;
//        this._loadData();
//    }
//
//    openComparisonDropdown(ev) {
//        ev.stopPropagation();
//        this.state.comparisonDropdownOpen = !this.state.comparisonDropdownOpen;
//    }
//
//    setComparisonMode(mode) {
//        this.state.comparisonMode = mode;
//        if (mode === "percentage_of") {
//            this.state.percentageOfPickerOpen = true;
//            return;
//        }
//        if (mode === "none") {
//            this.state.comparisonDropdownOpen = false;
//            this.state.comparisonColumns = [];
//        }
//        this._loadData();
//    }
//
//    setComparisonPeriodCount(ev) {
//        const val = parseInt(ev.target.value, 10);
//        this.state.comparisonPeriodCount = Math.max(1, Math.min(12, val || 1));
//        if (this.state.comparisonMode !== "none") {
//            this._loadData();
//        }
//    }
//
//    setComparisonFormat(format) {
//        this.state.comparisonFormat = format;
//    }
//
//    setPeriodOrder(order) {
//        this.state.periodOrder = order;
//    }
//
//    selectPercentageOfLine(lineId, lineName) {
//        this.state.percentageOfLineId = lineId;
//        this.state.percentageOfLineName = lineName;
//        this.state.percentageOfPickerOpen = false;
//        this.state.comparisonDropdownOpen = false;
//    }
//
//    togglePercentageOfPicker(ev) {
//        ev.stopPropagation();
//        this.state.comparisonMode = "percentage_of";
//        this.state.percentageOfPickerOpen = !this.state.percentageOfPickerOpen;
//    }
//
//    onComparisonDateFromChange(ev) {
//        this.state.comparisonDateFrom = ev.target.value;
//        this._loadData();
//    }
//
//    onComparisonDateToChange(ev) {
//        this.state.comparisonDateTo = ev.target.value;
//        this._loadData();
//    }
//
//    openOptionsDropdown(ev) {
//        ev.stopPropagation();
//        this.state.optionsDropdownOpen = !this.state.optionsDropdownOpen;
//    }
//
//    setTargetMove(mode) {
//        if (this.state.targetMove !== mode) {
//            this.state.targetMove = mode;
//            this._loadData();
//        }
//    }
//
//    dismissWarning() {
//        this.state.showUnpostedWarning = false;
//    }
//
//    isCollapsed(lineId) {
//        return this.state.collapsedSections.has(lineId);
//    }
//
//    toggleLine(line) {
//        if (!line.children || !line.children.length) return;
//        if (this.state.collapsedSections.has(line.id)) {
//            this.state.collapsedSections.delete(line.id);
//        } else {
//            this.state.collapsedSections.add(line.id);
//        }
//    }
//
//    isExpandable(line) {
//        return line.children && line.children.length > 0;
//    }
//
//    lineRowClass(line) {
//        const classes = ["oca-fs-row"];
//        classes.push(`oca-fs-style-${line.style || "default"}`);
//        classes.push(`oca-fs-level-${line.level || 0}`);
//        if (line.line_type === "subtotal") classes.push("oca-fs-subtotal");
//        if (line.line_type === "account" || line.line_type === "computed") {
//            classes.push("oca-fs-account");
//        }
//        if (line.style === "header") classes.push("oca-fs-header-band");
//        return classes.join(" ");
//    }
//
//    fmtNum(value) {
//        return fmtAmt(value);
//    }
//
//    fmtNumWithSym(value) {
//        const amt = fmtAmt(value);
//        const sym = this.state.currencySymbol || this.state.currencyName || "";
//        return sym ? `${amt} ${sym}` : amt;
//    }
//
//    openAccount(accountId) {
//        if (!accountId) return;
//        this.action.doAction({
//            type: "ir.actions.act_window",
//            res_model: "account.account",
//            res_id: accountId,
//            views: [[false, "form"]],
//            target: "current",
//        });
//    }
//
//    async exportPDF() {
//        if (this.state.exportingPdf) return;
//        this.state.exportingPdf = true;
//        try {
//            const result = await rpc("/oca_fs/export_pdf", {
//                report_type: this.state.reportType,
//                date_from: this.state.dateFrom,
//                date_to: this.state.dateTo,
//                company_id: this.state.companyId,
//                target_move: this.state.targetMove,
//            });
//            if (result?.file_content) {
//                const link = document.createElement("a");
//                link.href = "data:application/pdf;base64," + result.file_content;
//                link.download = result.file_name || "report.pdf";
//                document.body.appendChild(link);
//                link.click();
//                document.body.removeChild(link);
//            }
//        } catch (e) {
//            console.error("PDF export error:", e);
//            this.notification.add("PDF export failed. Please try again.", {
//                type: "danger",
//            });
//        } finally {
//            this.state.exportingPdf = false;
//        }
//    }
//
//    printReport() {
//        window.print();
//    }
//}
//
//registry
//    .category("actions")
//    .add("oca_fs.FinancialStatementsView", FinancialStatementsView);
/** @odoo-module **/
/**
 * OCA Financial Statements — Enterprise Interactive View
 * Balance Sheet & Profit and Loss with Enterprise-style layout.
 */
/** @odoo-module **/
/**
 * OCA Financial Statements — Enterprise Interactive View
 * Balance Sheet & Profit and Loss with Enterprise-style layout.
 */

import {
    Component,
    useState,
    onWillStart,
    onMounted,
    onWillUnmount,
    useRef,
} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

function fmtAmt(value, decimals = 2) {
    if (value === null || value === undefined) return "0.00";
    return Number(value).toLocaleString(undefined, {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
    });
}

function defaultDateFrom() {
    const d = new Date();
    return `${d.getFullYear()}-01-01`;
}

function defaultDateTo() {
    return new Date().toISOString().slice(0, 10);
}

function displayDate(isoStr) {
    if (!isoStr) return "";
    const [y, m, d] = isoStr.split("-");
    return `${d}/${m}/${y}`;
}

function isoDate(d) {
    return d.toISOString().slice(0, 10);
}

function subtractDays(isoStr, days) {
    const d = new Date(isoStr);
    d.setDate(d.getDate() - days);
    return isoDate(d);
}

function subtractMonths(isoStr, months) {
    const d = new Date(isoStr);
    d.setMonth(d.getMonth() - months);
    return isoDate(d);
}

function subtractYears(isoStr, years) {
    const d = new Date(isoStr);
    d.setFullYear(d.getFullYear() - years);
    return isoDate(d);
}

function periodLengthDays(dateFrom, dateTo) {
    const dFrom = new Date(dateFrom);
    const dTo = new Date(dateTo);
    return Math.ceil(Math.abs(dTo - dFrom) / (1000 * 60 * 60 * 24)) + 1;
}

export class FinancialStatementsView extends Component {
    static template = "oca_fs.FinancialStatementsView";
    static props = ["*"];

    setup() {
        this.action = useService("action");
        this.notification = useService("notification");

        const reportType =
            this.props.action?.params?.default_report_type || "bs";

        this.state = useState({
            reportType,
            lines: [],
            currencyName: "",
            currencySymbol: "",
            companyName: "",
            companyId: null,
            loading: false,
            error: null,
            exportingPdf: false,

            dateFrom: defaultDateFrom(),
            dateTo: defaultDateTo(),
            targetMove: "posted",

            collapsedSections: new Set(),
            showUnpostedWarning: true,
            hasUnposted: false,

            comparisonMode: "none",
            comparisonPeriodCount: 1,
            comparisonDateFrom: defaultDateFrom(),
            comparisonDateTo: defaultDateTo(),
            comparisonFormat: "absolute",
            periodOrder: "desc",
            percentageOfLineId: null,
            percentageOfLineName: "",
            percentageOfPickerOpen: false,
            comparisonColumns: [],

            comparisonDropdownOpen: false,
            optionsDropdownOpen: false,

            splitHorizontally: false,
        });

        this.comparisonDropdownRef = useRef("comparisonDropdownRef");
        this.optionsDropdownRef = useRef("optionsDropdownRef");

        onWillStart(async () => {
            await this._loadInitData();
            await this._loadData();
        });

        this._docClickHandler = this._onDocClick.bind(this);
        onMounted(() => {
            document.addEventListener("click", this._docClickHandler);
        });
        onWillUnmount(() => {
            document.removeEventListener("click", this._docClickHandler);
        });
    }

    _onDocClick(ev) {
        if (this.state.comparisonDropdownOpen) {
            const el = this.comparisonDropdownRef.el;
            if (el && !el.contains(ev.target)) {
                this.state.comparisonDropdownOpen = false;
                this.state.percentageOfPickerOpen = false;
            }
        }
        if (this.state.optionsDropdownOpen) {
            const el = this.optionsDropdownRef.el;
            if (el && !el.contains(ev.target)) {
                this.state.optionsDropdownOpen = false;
            }
        }
    }

    async _loadInitData() {
        try {
            const result = await rpc("/oca_fs/init", {
                company_id: this.state.companyId,
            });
            this.state.companyId = result.company_id;
            this.state.companyName = result.company_name;
            this.state.currencyName = result.currency_name;
            this.state.currencySymbol = result.currency_symbol;
            if (result.date_from) this.state.dateFrom = result.date_from;
            if (result.date_to) this.state.dateTo = result.date_to;
        } catch (e) {
            console.error("FS init error:", e);
        }
    }

    async _loadData() {
        this.state.loading = true;
        this.state.error = null;
        try {
            const compPeriods = this.getComparisonPeriods();
            const payload = {
                report_type: this.state.reportType,
                date_from: this.state.dateFrom,
                date_to: this.state.dateTo,
                company_id: this.state.companyId,
                target_move: this.state.targetMove,
                comparison_mode: this.state.comparisonMode,
            };
            if (
                compPeriods &&
                compPeriods.length &&
                this.state.comparisonMode !== "percentage_of"
            ) {
                payload.comparison_periods = compPeriods;
            }
            const result = await rpc("/oca_fs/get_data", payload);
            this.state.lines = result.lines || [];
            this.state.comparisonColumns = result.comparison_columns || [];
            this.state.currencyName = result.currency_name || this.state.currencyName;
            this.state.currencySymbol =
                result.currency_symbol || this.state.currencySymbol;
            this.state.companyName = result.company_name || this.state.companyName;
            this.state.hasUnposted = result.has_unposted || false;
        } catch (e) {
            console.error("FS data error:", e);
            this.state.error =
                "Failed to load report data. Please check the console for details.";
        } finally {
            this.state.loading = false;
        }
    }

    get reportTitle() {
        return this.state.reportType === "bs" ? "Balance Sheet" : "Profit and Loss";
    }

    get isBalanceSheet() {
        return this.state.reportType === "bs";
    }

    get showComparison() {
        return (
            this.state.comparisonMode !== "none" &&
            this.state.comparisonMode !== "percentage_of" &&
            this.orderedComparisonColumns.length > 0
        );
    }

    get showPercentageOf() {
        return (
            this.state.comparisonMode === "percentage_of" &&
            !!this.state.percentageOfLineId
        );
    }

    get showSplitHorizontally() {
        return this.state.splitHorizontally && this.isBalanceSheet;
    }

    get splitLeftLines() {
        return (this.state.lines || []).filter((l) => l.id === "assets");
    }

    get splitRightLines() {
        return (this.state.lines || []).filter((l) => l.id !== "assets");
    }

    get orderedComparisonColumns() {
        const cols = [...(this.state.comparisonColumns || [])];
        if (this.state.periodOrder === "asc") {
            cols.reverse();
        }
        return cols;
    }

    get dateFilterLabel() {
        if (this.isBalanceSheet) {
            return `As of ${displayDate(this.state.dateTo)}`;
        }
        const year = (this.state.dateTo || "").slice(0, 4);
        if (year) return year;
        return displayDate(this.state.dateFrom);
    }

    get optionsDropdownLabel() {
        return this.state.targetMove === "posted"
            ? "Posted Entries, Accrual Basis"
            : "Draft & Posted Entries, Accrual Basis";
    }

    get comparisonModeLabel() {
        if (this.state.comparisonMode === "none") return "Comparison";
        if (this.state.comparisonMode === "previous_period") {
            const n = this.state.comparisonPeriodCount;
            return n > 1 ? `Previous Period (${n})` : "Previous Period";
        }
        if (this.state.comparisonMode === "same_period_last_year") {
            const n = this.state.comparisonPeriodCount;
            return n > 1 ? `Same Period Last Year (${n})` : "Same Period Last Year";
        }
        if (this.state.comparisonMode === "percentage_of") {
            return this.state.percentageOfLineName
                ? `Comparison: ${this.state.percentageOfLineName}`
                : "Percentage of";
        }
        return "Specific Date";
    }

    getComparisonPeriods() {
        if (
            this.state.comparisonMode === "none" ||
            this.state.comparisonMode === "percentage_of"
        ) {
            return null;
        }

        const count = Math.max(1, Math.min(12, this.state.comparisonPeriodCount || 1));
        const periods = [];

        if (this.state.comparisonMode === "previous_period") {
            if (this.isBalanceSheet) {
                for (let i = 1; i <= count; i++) {
                    const compTo = subtractMonths(this.state.dateTo, i);
                    periods.push({
                        date_from: compTo,
                        date_to: compTo,
                        label: displayDate(compTo),
                    });
                }
            } else {
                const diffDays = periodLengthDays(
                    this.state.dateFrom,
                    this.state.dateTo
                );
                for (let i = 1; i <= count; i++) {
                    const shift = diffDays * i;
                    const compFrom = subtractDays(this.state.dateFrom, shift);
                    const compTo = subtractDays(this.state.dateTo, shift);
                    periods.push({
                        date_from: compFrom,
                        date_to: compTo,
                        label: `${displayDate(compFrom)} – ${displayDate(compTo)}`,
                    });
                }
            }
        } else if (this.state.comparisonMode === "same_period_last_year") {
            for (let i = 1; i <= count; i++) {
                if (this.isBalanceSheet) {
                    const compTo = subtractYears(this.state.dateTo, i);
                    periods.push({
                        date_from: compTo,
                        date_to: compTo,
                        label: displayDate(compTo),
                    });
                } else {
                    const compFrom = subtractYears(this.state.dateFrom, i);
                    const compTo = subtractYears(this.state.dateTo, i);
                    periods.push({
                        date_from: compFrom,
                        date_to: compTo,
                        label: `${displayDate(compFrom)} – ${displayDate(compTo)}`,
                    });
                }
            }
        } else if (this.state.comparisonMode === "specific_date") {
            periods.push({
                date_from: this.state.comparisonDateFrom,
                date_to: this.state.comparisonDateTo,
                label: this.isBalanceSheet
                    ? displayDate(this.state.comparisonDateTo)
                    : `${displayDate(this.state.comparisonDateFrom)} – ${displayDate(this.state.comparisonDateTo)}`,
            });
        }

        return periods;
    }

    getPercentageOfLines() {
        const result = [];
        const walk = (lines, depth = 0) => {
            for (const line of lines) {
                const selectable =
                    line.style === "header" ||
                    line.style === "group" ||
                    line.style === "subsection" ||
                    line.line_type === "subtotal";
                if (selectable) {
                    result.push({
                        id: line.id,
                        name: line.name,
                        level: depth,
                    });
                }
                if (line.children?.length) {
                    walk(line.children, depth + 1);
                }
            }
        };
        walk(this.state.lines);
        return result;
    }

    getLineBalanceById(lineId) {
        let found = 0;
        const walk = (lines) => {
            for (const line of lines) {
                if (line.id === lineId) {
                    found = line.balance || 0;
                    return true;
                }
                if (line.children?.length && walk(line.children)) return true;
            }
            return false;
        };
        walk(this.state.lines);
        return found;
    }

    getComparisonValue(line, compBalance) {
        if (this.state.comparisonFormat === "percentage") {
            const current = line.balance || 0;
            const comp = compBalance || 0;
            if (comp === 0) return comp === current ? 0 : null;
            return ((current - comp) / Math.abs(comp)) * 100;
        }
        return compBalance || 0;
    }

    fmtComparisonValue(line, compBalance) {
        const val = this.getComparisonValue(line, compBalance);
        if (val === null) return "n/a";
        if (this.state.comparisonFormat === "percentage") {
            return `${fmtAmt(val, 1)}%`;
        }
        return this.fmtNumWithSym(val);
    }

    getPercentageOfValue(line) {
        const base = this.getLineBalanceById(this.state.percentageOfLineId);
        if (!base) return 0;
        return ((line.balance || 0) / base) * 100;
    }

    fmtPctOf(line) {
        return `${fmtAmt(this.getPercentageOfValue(line), 1)}%`;
    }

    pctOfClass(line) {
        const pct = this.getPercentageOfValue(line);
        if (pct >= 50) return "oca-fs-pct-high";
        if (pct > 0) return "oca-fs-pct-mid";
        return "oca-fs-pct-zero";
    }

    getComparisonBalanceForColumn(line, colIndex) {
        const ordered = this.orderedComparisonColumns;
        if (!ordered.length || !line.comparison_balances) {
            return line.comparison_balance || 0;
        }
        const col = ordered[colIndex];
        if (!col) return 0;
        const match = line.comparison_balances.find(
            (cb) => cb.label === col.label && cb.date_to === col.date_to
        );
        return match ? match.balance : 0;
    }

    onDateFromChange(ev) {
        this.state.dateFrom = ev.target.value;
        this._loadData();
    }

    onDateToChange(ev) {
        this.state.dateTo = ev.target.value;
        this._loadData();
    }

    openComparisonDropdown(ev) {
        ev.stopPropagation();
        this.state.comparisonDropdownOpen = !this.state.comparisonDropdownOpen;
    }

    setComparisonMode(mode) {
        this.state.comparisonMode = mode;
        if (mode === "percentage_of") {
            this.state.percentageOfPickerOpen = true;
            return;
        }
        if (mode === "none") {
            this.state.comparisonDropdownOpen = false;
            this.state.comparisonColumns = [];
        }
        this._loadData();
    }

    setComparisonPeriodCount(ev) {
        const val = parseInt(ev.target.value, 10);
        this.state.comparisonPeriodCount = Math.max(1, Math.min(12, val || 1));
        if (this.state.comparisonMode !== "none") {
            this._loadData();
        }
    }

    setComparisonFormat(format) {
        this.state.comparisonFormat = format;
    }

    setPeriodOrder(order) {
        this.state.periodOrder = order;
    }

    selectPercentageOfLine(lineId, lineName) {
        this.state.percentageOfLineId = lineId;
        this.state.percentageOfLineName = lineName;
        this.state.percentageOfPickerOpen = false;
        this.state.comparisonDropdownOpen = false;
    }

    togglePercentageOfPicker(ev) {
        ev.stopPropagation();
        this.state.comparisonMode = "percentage_of";
        this.state.percentageOfPickerOpen = !this.state.percentageOfPickerOpen;
    }

    onComparisonDateFromChange(ev) {
        this.state.comparisonDateFrom = ev.target.value;
        this._loadData();
    }

    onComparisonDateToChange(ev) {
        this.state.comparisonDateTo = ev.target.value;
        this._loadData();
    }

    openOptionsDropdown(ev) {
        ev.stopPropagation();
        this.state.optionsDropdownOpen = !this.state.optionsDropdownOpen;
    }

    setTargetMove(mode) {
        if (this.state.targetMove !== mode) {
            this.state.targetMove = mode;
            this._loadData();
        }
    }

    toggleSplitHorizontally(ev) {
        if (ev) ev.stopPropagation();
        this.state.splitHorizontally = !this.state.splitHorizontally;
    }

    dismissWarning() {
        this.state.showUnpostedWarning = false;
    }

    isCollapsed(lineId) {
        return this.state.collapsedSections.has(lineId);
    }

    toggleLine(line) {
        if (!line.children || !line.children.length) return;
        if (this.state.collapsedSections.has(line.id)) {
            this.state.collapsedSections.delete(line.id);
        } else {
            this.state.collapsedSections.add(line.id);
        }
    }

    isExpandable(line) {
        return line.children && line.children.length > 0;
    }

    lineRowClass(line) {
        const classes = ["oca-fs-row"];
        classes.push(`oca-fs-style-${line.style || "default"}`);
        classes.push(`oca-fs-level-${line.level || 0}`);
        if (line.line_type === "subtotal") classes.push("oca-fs-subtotal");
        if (line.line_type === "account" || line.line_type === "computed") {
            classes.push("oca-fs-account");
        }
        if (line.style === "header") classes.push("oca-fs-header-band");
        return classes.join(" ");
    }

    fmtNum(value) {
        return fmtAmt(value);
    }

    fmtNumWithSym(value) {
        const amt = fmtAmt(value);
        const sym = this.state.currencySymbol || this.state.currencyName || "";
        return sym ? `${amt} ${sym}` : amt;
    }

    openAccount(accountId) {
        if (!accountId) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "account.account",
            res_id: accountId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async exportPDF() {
        if (this.state.exportingPdf) return;
        this.state.exportingPdf = true;
        try {
            const result = await rpc("/oca_fs/export_pdf", {
                report_type: this.state.reportType,
                date_from: this.state.dateFrom,
                date_to: this.state.dateTo,
                company_id: this.state.companyId,
                target_move: this.state.targetMove,
            });
            if (result?.file_content) {
                const link = document.createElement("a");
                link.href = "data:application/pdf;base64," + result.file_content;
                link.download = result.file_name || "report.pdf";
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            }
        } catch (e) {
            console.error("PDF export error:", e);
            this.notification.add("PDF export failed. Please try again.", {
                type: "danger",
            });
        } finally {
            this.state.exportingPdf = false;
        }
    }

    printReport() {
        window.print();
    }
}

registry
    .category("actions")
    .add("oca_fs.FinancialStatementsView", FinancialStatementsView);