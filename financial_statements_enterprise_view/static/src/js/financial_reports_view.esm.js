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

const FS_THEME_KEY = "fs_ent_theme";

function loadDarkMode() {
    try {
        const stored = localStorage.getItem(FS_THEME_KEY);
        if (stored !== null) return stored === "dark";
    } catch (e) {}
    return true; // default dark
}

function saveDarkMode(dark) {
    try {
        localStorage.setItem(FS_THEME_KEY, dark ? "dark" : "light");
    } catch (e) {}
}

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
    const d = new Date();
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
}

function displayDate(isoStr) {
    if (!isoStr) return "";
    const [y, m, d] = isoStr.split("-");
    return `${d}/${m}/${y}`;
}

function isoDate(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
}

function subtractDays(isoStr, days) {
    const d = new Date(isoStr);
    d.setDate(d.getDate() - days);
    return isoDate(d);
}

function subtractMonths(isoStr, months) {
    const d = new Date(isoStr);
    const targetMonth = d.getMonth() - months;
    const originalDay = d.getDate();
    // Setting the day to 1 first avoids JS's month-overflow behaviour
    // (e.g. Dec 31 minus 1 month would otherwise become Dec 1, not Nov 30).
    d.setDate(1);
    d.setMonth(targetMonth);
    const daysInTargetMonth = new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate();
    d.setDate(Math.min(originalDay, daysInTargetMonth));
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

// Returns the ISO date of the most recently completed fiscal year end
// (lastMonth/lastDay, 1-indexed month) strictly before `isoStr`. Used so
// "Previous Period" never re-shows the currently selected date as if it
// were a comparison column.
//
// FIX: the old version compared `new Date(isoStr)` (parsed as UTC
// midnight) against `new Date(y, m, d)` (built in the browser's local
// timezone) in the same `>=` check. For any positive-UTC-offset
// timezone (e.g. Saudi Arabia UTC+3, India UTC+5:30) this made "today's
// fiscal year end" look like it was already in the past, so the first
// comparison period silently duplicated the current period. Comparing
// plain Y/M/D integers instead of Date objects removes the timezone
// mismatch entirely.
function fiscalYearEndOnOrBefore(isoStr, lastMonth, lastDay) {
    const [y, m, day] = isoStr.split("-").map(Number);
    const daysInMonth = new Date(y, lastMonth, 0).getDate();
    const clampedDay = Math.min(lastDay, daysInMonth);

    // Has this year's fiscal-year-end date already passed, strictly
    // before isoStr? Compare (lastMonth, clampedDay) vs (m, day) as
    // plain numbers — no Date objects, no timezone involved.
    const notYetCompleted =
        lastMonth > m || (lastMonth === m && clampedDay >= day);

    const endYear = notYetCompleted ? y - 1 : y;
    const finalDaysInMonth = new Date(endYear, lastMonth, 0).getDate();
    const finalDay = Math.min(lastDay, finalDaysInMonth);

    return `${endYear}-${String(lastMonth).padStart(2, "0")}-${String(finalDay).padStart(2, "0")}`;
}

export class FinancialStatementsView extends Component {
    static template = "fs_enterprise.FinancialStatementsView";
    static props = ["*"];

    setup() {
        this.action = useService("action");
        this.notification = useService("notification");

        const reportType =
            this.props.action?.params?.default_report_type || "bs";

        const savedTheme = localStorage.getItem("fs_ent_theme") || "dark";

        this.state = useState({
            reportType,
            lines: [],
            currencyName: "",
            currencySymbol: "",
            currencyDigits: 2,
            companyName: "",
            companyId: null,
            loading: false,
            error: null,
            exportingPdf: false,
            exportingXlsx: false,

            dateFrom: defaultDateFrom(),
            dateTo: defaultDateTo(),
            targetMove: "posted",
            showDebitCredit: false,

            // Fiscal year end (defaults to calendar year until /fs_enterprise/init responds)
            fiscalYearLastDay: 31,
            fiscalYearLastMonth: 12,

            collapsedSections: new Set(),
            unfoldAll: false,
            hideZeroLines: false,
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

            // Analytic filtering
            analyticAccountIds: [],
            analyticAccounts: [],
            analyticDropdownOpen: false,
            analyticColumns: [],
            showUnassigned: false,

            // Date mode filtering
            monthYear: defaultMonthYear(),
            dateMode: "year",
            customDateFrom: "",
            customDateTo: "",
            dateDropdownOpen: false,

            // Theme
            theme: savedTheme,
        });

        this.comparisonDropdownRef = useRef("comparisonDropdownRef");
        this.optionsDropdownRef = useRef("optionsDropdownRef");
        this.dateDropdownRef = useRef("dateDropdownRef");
        this.analyticDropdownRef = useRef("analyticDropdownRef");

        onWillStart(async () => {
            const today = new Date();
            this.state.customDateFrom = `${today.getFullYear()}-01-01`;
            this.state.customDateTo = today.toISOString().slice(0, 10);
            await this._loadInitData();
            await this._loadAnalyticAccounts();
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
        if (this.state.dateDropdownOpen) {
            const el = this.dateDropdownRef.el;
            if (el && !el.contains(ev.target)) {
                this.state.dateDropdownOpen = false;
            }
        }
        if (this.state.analyticDropdownOpen) {
            const el = this.analyticDropdownRef.el;
            if (el && !el.contains(ev.target)) {
                this.state.analyticDropdownOpen = false;
            }
        }
    }

    async _loadInitData() {
        try {
            const result = await rpc("/fs_enterprise/init", {
                company_id: this.state.companyId,
            });
            this.state.companyId = result.company_id;
            this.state.companyName = result.company_name;
            this.state.currencyName = result.currency_name;
            this.state.currencySymbol = result.currency_symbol;
            this.state.currencyDigits = result.currency_digits ?? 2;
            this.state.fiscalYearLastDay = result.fiscalyear_last_day || 31;
            this.state.fiscalYearLastMonth = result.fiscalyear_last_month || 12;
        } catch (e) {
            console.error("FS init error:", e);
        }
    }

    async _loadAnalyticAccounts() {
        try {
            const result = await rpc("/fs_enterprise/get_analytic_accounts", {
                company_id: this.state.companyId,
            });
            this.state.analyticAccounts = result || [];
        } catch (e) {
            console.error("FS load analytic accounts error:", e);
        }
    }

    _getDateRange() {
        if (this.state.dateMode === "month") {
            return monthYearToRange(this.state.monthYear);
        } else if (this.state.dateMode === "quarter") {
            const r = quarterToRange(this.state.monthYear);
            return { date_from: r.date_from, date_to: r.date_to };
        } else if (this.state.dateMode === "year") {
            return yearToRange(this.state.monthYear);
        } else {
            return {
                date_from: this.state.customDateFrom,
                date_to: this.state.customDateTo,
            };
        }
    }

    async _loadData() {
        // Race-condition guard: only the LATEST request may update the
        // screen. On big databases a report takes seconds; if the user
        // changes a filter meanwhile, an older (slower) response must
        // never overwrite the newer one.
        const seq = (this._loadSeq = (this._loadSeq || 0) + 1);
        this.state.loading = true;
        this.state.error = null;
        try {
            const range = this._getDateRange();
            this.state.dateFrom = range.date_from;
            this.state.dateTo = range.date_to;
            const compPeriods = this.getComparisonPeriods();
            const payload = {
                report_type: this.state.reportType,
                date_from: this.state.dateFrom,
                date_to: this.state.dateTo,
                company_id: this.state.companyId,
                target_move: this.state.targetMove,
                comparison_mode: this.state.comparisonMode,
                analytic_account_ids: this.state.analyticAccountIds,
                include_unassigned: this.state.showUnassigned,
                with_debit_credit: this.state.showDebitCredit,
            };
            if (
                compPeriods &&
                compPeriods.length &&
                this.state.comparisonMode !== "percentage_of"
            ) {
                payload.comparison_periods = compPeriods;
            }
            const result = await rpc("/fs_enterprise/get_data", payload);
            if (seq !== this._loadSeq) return; // stale response
            this.state.lines = result.lines || [];
            this.state.comparisonColumns = result.comparison_columns || [];
            this.state.analyticColumns = result.analytic_columns || [];
            this.state.currencyName = result.currency_name || this.state.currencyName;
            this.state.currencySymbol =
                result.currency_symbol || this.state.currencySymbol;
            if (result.currency_digits !== undefined) this.state.currencyDigits = result.currency_digits;
            this.state.companyName = result.company_name || this.state.companyName;
            this.state.hasUnposted = result.has_unposted || false;
            // Keep the fold state in sync with the freshly loaded lines:
            // stays collapsed (normal view) by default, or stays fully
            // expanded if "Unfold All" was already active.
            this._applyFoldState();
        } catch (e) {
            if (seq !== this._loadSeq) return; // stale request failed
            console.error("FS data error:", e);
            this.state.error =
                "Failed to load report data. Please check the console for details.";
        } finally {
            if (seq === this._loadSeq) {
                this.state.loading = false;
            }
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
        return this.visibleLines.filter((l) => l.id === "assets");
    }

    get splitRightLines() {
        return this.visibleLines.filter((l) => l.id !== "assets");
    }

    get orderedComparisonColumns() {
        const cols = [...(this.state.comparisonColumns || [])];
        if (this.state.periodOrder === "asc") {
            cols.reverse();
        }
        return cols;
    }

    get currentColumnLabel() {
        if (this.isBalanceSheet) {
            return displayDate(this.state.dateTo);
        }
        return `${displayDate(this.state.dateFrom)} \u2013 ${displayDate(this.state.dateTo)}`;
    }

    get dateFilterLabel() {
        let label = "";
        if (this.state.dateMode === "month") {
            label = monthYearDisplay(this.state.monthYear);
        } else if (this.state.dateMode === "quarter") {
            label = quarterDisplay(this.state.monthYear);
        } else if (this.state.dateMode === "year") {
            label = yearDisplay(this.state.monthYear);
        } else {
            label = `${displayDate(this.state.customDateFrom)} – ${displayDate(this.state.customDateTo)}`;
        }
        if (this.isBalanceSheet) {
            return `As of ${label.split(" – ").pop()}`;
        }
        return label;
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
                const mostRecentFyEnd = fiscalYearEndOnOrBefore(
                    this.state.dateTo,
                    this.state.fiscalYearLastMonth,
                    this.state.fiscalYearLastDay
                );
                for (let i = 1; i <= count; i++) {
                    const compTo = subtractYears(mostRecentFyEnd, i - 1);
                    periods.push({
                        date_from: compTo,
                        date_to: compTo,
                        label: displayDate(compTo),
                    });
                }
            } else {
                // FIX: calendar-aware previous period (not day-count) - prevents Jan 1 missing, Feb truncation, etc.
                if (this.state.dateMode === "month") {
                    for (let i = 1; i <= count; i++) {
                        const compMY = subtractMonthYears(this.state.monthYear, i);
                        const range = monthYearToRange(compMY);
                        periods.push({
                            date_from: range.date_from,
                            date_to: range.date_to,
                            label: `${displayDate(range.date_from)} – ${displayDate(range.date_to)}`,
                        });
                    }
                } else if (this.state.dateMode === "quarter") {
                    for (let i = 1; i <= count; i++) {
                        const compMY = subtractMonthYears(this.state.monthYear, i * 3);
                        const range = quarterToRange(compMY);
                        periods.push({
                            date_from: range.date_from,
                            date_to: range.date_to,
                            label: `${displayDate(range.date_from)} – ${displayDate(range.date_to)}`,
                        });
                    }
                } else if (this.state.dateMode === "year") {
                    for (let i = 1; i <= count; i++) {
                        const [y] = this.state.monthYear.split("-").map(Number);
                        const compY = y - i;
                        const compMY = `${compY}-01`;
                        const range = yearToRange(compMY);
                        periods.push({
                            date_from: range.date_from,
                            date_to: range.date_to,
                            label: `${displayDate(range.date_from)} – ${displayDate(range.date_to)}`,
                        });
                    }
                } else {
                    // custom: gapless - previous period ends day before current start
                    const diffDays = periodLengthDays(this.state.dateFrom, this.state.dateTo);
                    let curEnd = subtractDays(this.state.dateFrom, 1);
                    for (let i = 1; i <= count; i++) {
                        const curStart = subtractDays(curEnd, diffDays - 1);
                        periods.push({
                            date_from: curStart,
                            date_to: curEnd,
                            label: `${displayDate(curStart)} – ${displayDate(curEnd)}`,
                        });
                        curEnd = subtractDays(curStart, 1);
                    }
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
        if (pct >= 50) return "fs-ent-pct-high";
        if (pct > 0) return "fs-ent-pct-mid";
        return "fs-ent-pct-zero";
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

    openDateDropdown(ev) {
        ev.stopPropagation();
        this.state.dateDropdownOpen = !this.state.dateDropdownOpen;
    }

    setDateMode(mode) {
        this.state.dateMode = mode;
        this.state.dateDropdownOpen = false;
        this._loadData();
    }

    onMonthYearChange(ev) {
        this.state.monthYear = ev.target.value;
        this._loadData();
    }

    onCustomDateFromChange(ev) {
        this.state.customDateFrom = ev.target.value;
        this._loadData();
    }

    onCustomDateToChange(ev) {
        this.state.customDateTo = ev.target.value;
        this._loadData();
    }

    shiftPeriod(direction, ev) {
        if (ev) ev.stopPropagation();
        const [y, m] = this.state.monthYear.split("-").map(Number);
        let d = new Date(y, m - 1, 1);
        if (this.state.dateMode === "month") {
            d.setMonth(d.getMonth() + direction);
        } else if (this.state.dateMode === "quarter") {
            d.setMonth(d.getMonth() + direction * 3);
        } else if (this.state.dateMode === "year") {
            d.setFullYear(d.getFullYear() + direction);
        }
        const ny = d.getFullYear();
        const nm = String(d.getMonth() + 1).padStart(2, "0");
        this.state.monthYear = `${ny}-${nm}`;
        this._loadData();
    }

    _monthYearDisplay(my) {
        return monthYearDisplay(my);
    }

    _monthYearDisplayLong(my) {
        return monthYearDisplayLong(my);
    }

    _quarterDisplay(my) {
        return quarterDisplay(my);
    }

    _quarterDisplayRange(my) {
        return quarterDisplayRange(my);
    }

    _yearDisplay(my) {
        return yearDisplay(my);
    }

    openAnalyticDropdown(ev) {
        ev.stopPropagation();
        this.state.analyticDropdownOpen = !this.state.analyticDropdownOpen;
    }

    toggleAnalyticAccount(accountId) {
        const ids = this.state.analyticAccountIds;
        const idx = ids.indexOf(accountId);
        if (idx === -1) {
            ids.push(accountId);
        } else {
            ids.splice(idx, 1);
        }
        // Dropdown stays open so multiple accounts can be picked in one go.
        this._loadData();
    }

    clearAnalyticFilter(ev) {
        if (ev) ev.stopPropagation();
        this.state.analyticAccountIds = [];
        this.state.showUnassigned = false;
        this.state.analyticColumns = [];
        this._loadData();
    }

    toggleUnassigned() {
        // Shows / hides the extra "Unassigned" column (journal lines with
        // no analytic distribution, or only partially distributed).
        this.state.showUnassigned = !this.state.showUnassigned;
        this._loadData();
    }

    get hasAnalyticFilter() {
        return this.state.analyticAccountIds.length > 0 || this.state.showUnassigned;
    }

    get analyticFilterLabel() {
        const ids = this.state.analyticAccountIds;
        const un = this.state.showUnassigned;
        if (!ids.length) {
            return un ? "Unassigned" : "Analytic Account";
        }
        const base = ids.length === 1
            ? (this.state.analyticAccounts.find((a) => a.id === ids[0])?.name || "Analytic")
            : `${ids.length} Analytic Accounts`;
        return un ? `${base} + Unassigned` : base;
    }

    get showAnalyticColumns() {
        return this.state.analyticColumns && this.state.analyticColumns.length > 0;
    }

    getAnalyticBalance(line, analyticId) {
        if (!line.analytic_balances) return 0;
        return line.analytic_balances[analyticId] || 0;
    }

    fmtAnalyticBalance(line, analyticId) {
        const val = this.getAnalyticBalance(line, analyticId);
        return this.fmtNumWithSym(val);
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

    toggleDebitCredit(ev) {
        if (ev) ev.stopPropagation();
        this.state.showDebitCredit = !this.state.showDebitCredit;
        this._loadData();
    }

    toggleUnfoldAll(ev) {
        if (ev) ev.stopPropagation();
        this.state.unfoldAll = !this.state.unfoldAll;
        this._applyFoldState();
    }

    /**
     * Recursively collects the ids of every line that has children
     * (i.e. every line that can be folded/unfolded).
     */
    _getFoldableLineIds(lines) {
        const ids = [];
        for (const line of lines || []) {
            if (line.children && line.children.length) {
                ids.push(line.id);
                ids.push(...this._getFoldableLineIds(line.children));
            }
        }
        return ids;
    }

    /**
     * Syncs collapsedSections with the current unfoldAll flag:
     * - unfoldAll = true  -> every section expanded (detail view)
     * - unfoldAll = false -> every section collapsed (normal/summary view)
     */
    _applyFoldState() {
        this.state.collapsedSections = this.state.unfoldAll
            ? new Set()
            : new Set(this._getFoldableLineIds(this.state.lines));
    }

    toggleHideZeroLines(ev) {
        if (ev) ev.stopPropagation();
        this.state.hideZeroLines = !this.state.hideZeroLines;
    }

    _filterZeroLines(lines) {
        const result = [];
        // FIX: use currency-aware threshold like backend _zero_threshold()
        const digits = this.state.currencyDigits ?? 2;
        const threshold = 0.5 * Math.pow(10, -digits);
        for (const line of lines) {
            let children = line.children;
            if (children && children.length) {
                children = this._filterZeroLines(children);
            } else {
                children = line.children || [];
            }
            const hasNonZeroBalance = Math.abs(line.balance || 0) >= threshold;
            if (hasNonZeroBalance || children.length) {
                result.push({ ...line, children });
            }
        }
        return result;
    }

    get visibleLines() {
        return this.state.hideZeroLines
            ? this._filterZeroLines(this.state.lines || [])
            : this.state.lines;
    }

    dismissWarning() {
        this.state.showUnpostedWarning = false;
    }

    isCollapsed(lineId) {
        if (this.state.unfoldAll) return false;
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
        const classes = ["fs-ent-row"];
        classes.push(`fs-ent-style-${line.style || "default"}`);
        classes.push(`fs-ent-level-${line.level || 0}`);
        if (line.line_type === "subtotal") classes.push("fs-ent-subtotal");
        if (line.line_type === "account" || line.line_type === "computed") {
            classes.push("fs-ent-account");
        }
        if (line.style === "header") classes.push("fs-ent-header-band");
        return classes.join(" ");
    }

    fmtNum(value) {
        const d = this.state.currencyDigits ?? 2;
        return fmtAmt(value, d);
    }

    fmtNumWithSym(value) {
        const d = this.state.currencyDigits ?? 2;
        const amt = fmtAmt(value, d);
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

    /**
     * True if a line can be drilled into: either a single-account leaf
     * (line.account_id) or a computed line backed by several accounts
     * (line.account_ids), e.g. Current/Previous Year Unallocated Earnings.
     */
    hasDrilldown(line) {
        return !!(line && (line.account_id || (line.account_ids && line.account_ids.length)));
    }

    /**
     * Click handler bound to amount cells. Only drillable lines open
     * journal items; for header/subtotal/total rows the click is left
     * to bubble up so the existing row-toggle (expand/collapse) behavior
     * keeps working exactly as before.
     */
    onBalanceClick(ev, line, customDates = null) {
        if (!this.hasDrilldown(line)) {
            return;
        }
        ev.stopPropagation();
        this.openJournalItems(line, customDates);
    }

    /**
     * Drill down from a Balance Sheet / P&L amount into the underlying
     * journal items (account.move.line).
     *
     * @param {Object} line - a leaf report line (line.account_id) or a
     *      computed line backed by several accounts (line.account_ids),
     *      e.g. "Current Year Unallocated Earnings".
     * @param {Object|null} customDates - optional {date_from, date_to} used
     *      when drilling into a comparison-period column instead of the
     *      main column.
     */
    openJournalItems(line, customDates = null) {
        if (!this.hasDrilldown(line)) {
            return;
        }
        const accountIds =
            line.account_ids && line.account_ids.length
                ? line.account_ids
                : [line.account_id];

        let dateFrom, dateTo;
        if (customDates) {
            dateFrom = customDates.date_from;
            dateTo = customDates.date_to;
        } else if (line.line_type === "computed") {
            // Current/Previous Year Unallocated Earnings carry their own
            // fiscal-year-bound date range from the engine.
            dateFrom = line.date_from;
            dateTo = line.date_to;
        } else {
            dateFrom = this.state.dateFrom;
            dateTo = this.state.dateTo;
        }

        const domain = [
            ["company_id", "=", this.state.companyId],
            ["account_id", "in", accountIds],
            ["display_type", "not in", ["line_section", "line_note"]],
        ];

        if (dateTo) {
            domain.push(["date", "<=", dateTo]);
        }
        // Regular Balance Sheet account lines are cumulative to the date (no
        // lower bound, matching the engine). The P&L, and the computed
        // Current/Previous Year Unallocated Earnings lines on the Balance
        // Sheet, are bound to a specific period.
        if (
            dateFrom &&
            (this.state.reportType !== "bs" || line.line_type === "computed" || customDates)
        ) {
            domain.push(["date", ">=", dateFrom]);
        }

        const targetMove = this.state.targetMove;
        // FIX: use parent_state (stored indexed field) like backend _move_state_domain
        if (targetMove === "posted") {
            domain.push(["parent_state", "=", "posted"]);
        } else if (targetMove === "draft") {
            domain.push(["parent_state", "=", "draft"]);
        } else {
            domain.push(["parent_state", "!=", "cancel"]);
        }

        const hasIds = this.state.analyticAccountIds && this.state.analyticAccountIds.length;
        if (hasIds && this.state.showUnassigned) {
            domain.push("|");
            domain.push(["analytic_distribution", "in", this.state.analyticAccountIds]);
            domain.push(["analytic_distribution", "=", false]);
        } else if (hasIds) {
            domain.push(["analytic_distribution", "in", this.state.analyticAccountIds]);
        } else if (this.state.showUnassigned) {
            domain.push(["analytic_distribution", "=", false]);
        }

        this.action.doAction({
            type: "ir.actions.act_window",
            name: `${line.name} \u2014 Journal Items`,
            res_model: "account.move.line",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: domain,
            target: "current",
        });
    }

    async exportPDF() {
        if (this.state.exportingPdf) return;
        this.state.exportingPdf = true;
        try {
            const compPeriods = this.getComparisonPeriods();
            const payload = {
                report_type: this.state.reportType,
                date_from: this.state.dateFrom,
                date_to: this.state.dateTo,
                company_id: this.state.companyId,
                target_move: this.state.targetMove,
                comparison_mode: this.state.comparisonMode,
                analytic_account_ids: this.state.analyticAccountIds,
                include_unassigned: this.state.showUnassigned,
                with_debit_credit: this.state.showDebitCredit,
            };
            if (
                compPeriods &&
                compPeriods.length &&
                this.state.comparisonMode !== "percentage_of"
            ) {
                payload.comparison_periods = compPeriods;
            }
            const result = await rpc("/fs_enterprise/export_pdf", payload);
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

    async exportExcel() {
        if (this.state.exportingXlsx) return;
        this.state.exportingXlsx = true;
        try {
            const compPeriods = this.getComparisonPeriods();
            const range = this._getDateRange();
            const payload = {
                report_type: this.state.reportType,
                date_from: range.date_from,
                date_to: range.date_to,
                company_id: this.state.companyId,
                target_move: this.state.targetMove,
                comparison_mode: this.state.comparisonMode,
                analytic_account_ids: this.state.analyticAccountIds,
                include_unassigned: this.state.showUnassigned,
                with_debit_credit: this.state.showDebitCredit,
            };
            if (
                compPeriods &&
                compPeriods.length &&
                this.state.comparisonMode !== "percentage_of"
            ) {
                payload.comparison_periods = compPeriods;
            }
            const result = await rpc("/fs_enterprise/export_excel", payload);
            if (result?.file_content) {
                const link = document.createElement("a");
                link.href = "data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64," + result.file_content;
                const title = this.state.reportType === "bs" ? "Balance_Sheet" : "Profit_and_Loss";
                link.download = result.file_name || `${title}.xlsx`;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            }
        } catch (e) {
            console.error("Excel export error:", e);
            this.notification.add("Excel export failed. Please try again.", {
                type: "danger",
            });
        } finally {
            this.state.exportingXlsx = false;
        }
    }

    closeReport() {
        window.history.back();
    }

    toggleTheme(ev) {
        if (ev) ev.stopPropagation();
        this.state.theme = this.state.theme === "dark" ? "light" : "dark";
        localStorage.setItem("fs_ent_theme", this.state.theme);
    }
}

registry
    .category("actions")
    .add("fs_enterprise.FinancialStatementsView", FinancialStatementsView);

// =====================================================================
// TaxReportView — VAT Return (Enterprise-style)
// =====================================================================

function defaultMonthYear() {
    const d = new Date();
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    return `${y}-${m}`;
}

function monthYearToRange(my) {
    const [y, m] = my.split("-").map(Number);
    const lastDay = new Date(y, m, 0).getDate();
    return {
        date_from: `${y}-${String(m).padStart(2, "0")}-01`,
        date_to: `${y}-${String(m).padStart(2, "0")}-${String(lastDay).padStart(2, "0")}`,
    };
}

function monthYearDisplay(my) {
    if (!my) return "";
    const [y, m] = my.split("-");
    const months = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ];
    return `${months[parseInt(m, 10) - 1]} ${y}`;
}

function monthYearDisplayLong(my) {
    if (!my) return "";
    const [y, m] = my.split("-");
    const months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ];
    return `${months[parseInt(m, 10) - 1]} ${y}`;
}

function subtractMonthYears(my, count) {
    const [y, m] = my.split("-").map(Number);
    const d = new Date(y, m - 1 - count, 1);
    const ny = d.getFullYear();
    const nm = String(d.getMonth() + 1).padStart(2, "0");
    return `${ny}-${nm}`;
}

function quarterToRange(my) {
    const [y, m] = my.split("-").map(Number);
    const qStart = Math.floor((m - 1) / 3) * 3 + 1;
    const qEnd = qStart + 2;
    const qEndLastDay = new Date(y, qEnd, 0).getDate();
    const qStartStr = `${y}-${String(qStart).padStart(2, "0")}-01`;
    const qEndStr = `${y}-${String(qEnd).padStart(2, "0")}-${String(qEndLastDay).padStart(2, "0")}`;
    const qNames = ["Q1", "Q2", "Q3", "Q4"];
    return {
        date_from: qStartStr,
        date_to: qEndStr,
        label: `${qNames[Math.floor((m - 1) / 3)]} ${y}`,
    };
}

function quarterDisplay(my) {
    if (!my) return "";
    const [y, m] = my.split("-").map(Number);
    const q = Math.floor((m - 1) / 3);
    const qNames = ["Q1", "Q2", "Q3", "Q4"];
    const qStart = q * 3 + 1;
    const qEnd = qStart + 2;
    const months = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ];
    return `${qNames[q]} ${y} - ${months[qEnd - 1]} ${y}`;
}

function quarterDisplayRange(my) {
    if (!my) return "";
    const [y, m] = my.split("-").map(Number);
    const q = Math.floor((m - 1) / 3);
    const qStart = q * 3 + 1;
    const qEnd = qStart + 2;
    const months = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ];
    return `${months[qStart - 1]} ${y} - ${months[qEnd - 1]} ${y}`;
}

function yearToRange(my) {
    const [y] = my.split("-").map(Number);
    return {
        date_from: `${y}-01-01`,
        date_to: `${y}-12-31`,
        label: `${y}`,
    };
}

function yearDisplay(my) {
    if (!my) return "";
    const [y] = my.split("-").map(Number);
    return `${y}`;
}

export class TaxReportView extends Component {
    static template = "fs_enterprise.TaxReportView";
    static props = ["*"];

    setup() {
        this.action = useService("action");
        this.notification = useService("notification");

        const savedTaxTheme = localStorage.getItem("fs_ent_theme") || "dark";

        this.state = useState({
            lines: [],
            currencyName: "",
            currencySymbol: "",
            currencyDigits: 2,
            companyName: "",
            companyId: null,
            loading: false,
            error: null,

            monthYear: defaultMonthYear(),
            dateMode: "month",
            customDateFrom: "",
            customDateTo: "",
            showPosted: true,
            showDraft: false,
            hideZeroLines: false,
            hasUnposted: false,
            showUnpostedWarning: true,

            exportingPdf: false,
            exportingXlsx: false,
            dateDropdownOpen: false,
            optionsDropdownOpen: false,
            comparisonDropdownOpen: false,
            comparisonMode: "none",
            comparisonPeriodCount: 2,
            comparisonColumns: [],
            periodOrder: "desc",

            // Analytic filtering
            analyticAccountIds: [],
            analyticAccounts: [],
            analyticDropdownOpen: false,

            // Theme
            theme: savedTaxTheme,
        });

        this.dateDropdownRef = useRef("taxDateDropdownRef");
        this.optionsDropdownRef = useRef("taxOptionsDropdownRef");
        this.comparisonDropdownRef = useRef("taxComparisonDropdownRef");
        this.analyticDropdownRef = useRef("taxAnalyticDropdownRef");

        onWillStart(async () => {
            const today = new Date();
            this.state.customDateFrom = `${today.getFullYear()}-01-01`;
            this.state.customDateTo = today.toISOString().slice(0, 10);
            await this._loadInitData();
            await this._loadAnalyticAccounts();
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
        if (this.state.dateDropdownOpen) {
            const el = this.dateDropdownRef.el;
            if (el && !el.contains(ev.target)) {
                this.state.dateDropdownOpen = false;
            }
        }
        if (this.state.optionsDropdownOpen) {
            const el = this.optionsDropdownRef.el;
            if (el && !el.contains(ev.target)) {
                this.state.optionsDropdownOpen = false;
            }
        }
        if (this.state.comparisonDropdownOpen) {
            const el = this.comparisonDropdownRef.el;
            if (el && !el.contains(ev.target)) {
                this.state.comparisonDropdownOpen = false;
            }
        }
        if (this.state.analyticDropdownOpen) {
            const el = this.analyticDropdownRef.el;
            if (el && !el.contains(ev.target)) {
                this.state.analyticDropdownOpen = false;
            }
        }
    }

    _getDateRange() {
        if (this.state.dateMode === "month") {
            return monthYearToRange(this.state.monthYear);
        } else if (this.state.dateMode === "quarter") {
            const r = quarterToRange(this.state.monthYear);
            return { date_from: r.date_from, date_to: r.date_to };
        } else if (this.state.dateMode === "year") {
            return yearToRange(this.state.monthYear);
        } else {
            return {
                date_from: this.state.customDateFrom,
                date_to: this.state.customDateTo,
            };
        }
    }

    async _loadInitData() {
        try {
            const result = await rpc("/fs_enterprise/init", {
                company_id: this.state.companyId,
            });
            this.state.companyId = result.company_id;
            this.state.companyName = result.company_name;
            this.state.currencyName = result.currency_name;
            this.state.currencySymbol = result.currency_symbol;
            if (result.currency_digits !== undefined) this.state.currencyDigits = result.currency_digits;
        } catch (e) {
            console.error("Tax Report init error:", e);
        }
    }

    async _loadAnalyticAccounts() {
        try {
            const result = await rpc("/fs_enterprise/get_analytic_accounts", {
                company_id: this.state.companyId,
            });
            this.state.analyticAccounts = result || [];
        } catch (e) {
            console.error("Tax Report load analytic accounts error:", e);
        }
    }

    openAnalyticDropdown(ev) {
        ev.stopPropagation();
        this.state.analyticDropdownOpen = !this.state.analyticDropdownOpen;
    }

    toggleAnalyticAccount(accountId) {
        const ids = this.state.analyticAccountIds;
        const idx = ids.indexOf(accountId);
        if (idx === -1) {
            ids.push(accountId);
        } else {
            ids.splice(idx, 1);
        }
        // Dropdown stays open so multiple accounts can be picked in one go.
        this._loadData();
    }

    clearAnalyticFilter(ev) {
        if (ev) ev.stopPropagation();
        this.state.analyticAccountIds = [];
        this._loadData();
    }

    async _loadData() {
        // Race-condition guard: only the LATEST request may update the
        // screen. On big databases a report takes seconds; if the user
        // changes a filter meanwhile, an older (slower) response must
        // never overwrite the newer one.
        const seq = (this._loadSeq = (this._loadSeq || 0) + 1);
        this.state.loading = true;
        this.state.error = null;
        try {
            const range = this._getDateRange();
            const payload = {
                date_from: range.date_from,
                date_to: range.date_to,
                company_id: this.state.companyId,
                target_move: this.targetMoveValue,
                analytic_account_ids: this.state.analyticAccountIds,
            };
            if (this.state.comparisonMode !== "none") {
                const periods = this._getComparisonPeriods();
                if (periods && periods.length) {
                    payload.comparison_periods = periods;
                }
            }
            const result = await rpc("/fs_enterprise/get_tax_report", payload);
            if (seq !== this._loadSeq) return; // stale response
            this.state.lines = result.lines || [];
            this.state.comparisonColumns = result.comparison_columns || [];
            this.state.currencyName = result.currency_name || this.state.currencyName;
            this.state.currencySymbol = result.currency_symbol || this.state.currencySymbol;
            this.state.companyName = result.company_name || this.state.companyName;
            this.state.hasUnposted = result.has_unposted || false;
        } catch (e) {
            if (seq !== this._loadSeq) return; // stale request failed
            console.error("Tax Report data error:", e);
            this.state.error = "Failed to load tax report data. Please check the console.";
        } finally {
            if (seq === this._loadSeq) {
                this.state.loading = false;
            }
        }
    }

    _getComparisonPeriods() {
        if (this.state.comparisonMode === "none") return null;
        const count = Math.max(1, Math.min(12, this.state.comparisonPeriodCount || 1));
        const periods = [];
        const [curY, curM] = this.state.monthYear.split("-").map(Number);
        for (let i = 1; i <= count; i++) {
            let compMY;
            if (this.state.comparisonMode === "same_period_last_year") {
                compMY = `${curY - i}-${String(curM).padStart(2, "0")}`;
            } else if (this.state.dateMode === "year") {
                compMY = `${curY - i}-${String(curM).padStart(2, "0")}`;
            } else if (this.state.dateMode === "quarter") {
                compMY = subtractMonthYears(this.state.monthYear, i * 3);
            } else {
                compMY = subtractMonthYears(this.state.monthYear, i);
            }
            let range;
            if (this.state.dateMode === "quarter") {
                const qr = quarterToRange(compMY);
                range = { date_from: qr.date_from, date_to: qr.date_to };
            } else if (this.state.dateMode === "year") {
                range = yearToRange(compMY);
            } else {
                range = monthYearToRange(compMY);
            }
            let label;
            if (this.state.dateMode === "month") {
                label = monthYearDisplay(compMY);
            } else if (this.state.dateMode === "quarter") {
                label = quarterDisplay(compMY);
            } else if (this.state.dateMode === "year") {
                label = yearDisplay(compMY);
            } else {
                label = `${range.date_from} - ${range.date_to}`;
            }
            periods.push({
                date_from: range.date_from,
                date_to: range.date_to,
                label: label,
            });
        }
        return periods;
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
        return "Comparison";
    }

    get showComparison() {
        return (
            this.state.comparisonMode !== "none" &&
            this.state.comparisonColumns.length > 0
        );
    }

    get orderedComparisonColumns() {
        // comparisonColumns arrives from the backend already ordered
        // most-recent-first (1 period back, 2 periods back, ...), which
        // is "descending" order. Only reverse it when the user explicitly
        // wants ascending (oldest-first) order.
        const cols = [...(this.state.comparisonColumns || [])];
        if (this.state.periodOrder === "asc") {
            cols.reverse();
        }
        return cols;
    }

    getComparisonBaseForColumn(line, colIndex) {
        const ordered = this.orderedComparisonColumns;
        if (!ordered.length || !line.comparison_balances) {
            return 0;
        }
        const col = ordered[colIndex];
        if (!col) return 0;
        const match = line.comparison_balances.find(
            (cb) => cb.label === col.label && cb.date_to === col.date_to
        );
        return match ? match.base_amount || 0 : 0;
    }

    getComparisonVatForColumn(line, colIndex) {
        const ordered = this.orderedComparisonColumns;
        if (!ordered.length || !line.comparison_balances) {
            return 0;
        }
        const col = ordered[colIndex];
        if (!col) return 0;
        const match = line.comparison_balances.find(
            (cb) => cb.label === col.label && cb.date_to === col.date_to
        );
        return match ? match.vat_amount || 0 : 0;
    }

    get dateFilterLabel() {
        if (this.state.dateMode === "month") {
            return monthYearDisplay(this.state.monthYear);
        } else if (this.state.dateMode === "quarter") {
            return quarterDisplay(this.state.monthYear);
        } else if (this.state.dateMode === "year") {
            return yearDisplay(this.state.monthYear);
        } else {
            const from = this.state.customDateFrom || "";
            const to = this.state.customDateTo || "";
            if (from && to) return `${from} - ${to}`;
            return "Custom Dates";
        }
    }

    _monthYearDisplay(my) {
        return monthYearDisplay(my);
    }

    _monthYearDisplayLong(my) {
        return monthYearDisplayLong(my);
    }

    _quarterDisplay(my) {
        return quarterDisplay(my);
    }

    _quarterDisplayRange(my) {
        return quarterDisplayRange(my);
    }

    _yearDisplay(my) {
        return yearDisplay(my);
    }

    shiftPeriod(direction, ev) {
        if (ev) ev.stopPropagation();
        const [y, m] = this.state.monthYear.split("-").map(Number);
        let d = new Date(y, m - 1, 1);
        if (this.state.dateMode === 'month') {
            d.setMonth(d.getMonth() + direction);
        } else if (this.state.dateMode === 'quarter') {
            d.setMonth(d.getMonth() + direction * 3);
        } else if (this.state.dateMode === 'year') {
            d.setFullYear(d.getFullYear() + direction);
        }
        const ny = d.getFullYear();
        const nm = String(d.getMonth() + 1).padStart(2, "0");
        this.state.monthYear = `${ny}-${nm}`;
        this._loadData();
    }

    get targetMoveValue() {
        if (this.state.showPosted && this.state.showDraft) return "all";
        if (this.state.showDraft && !this.state.showPosted) return "draft";
        return "posted";
    }

    get optionsDropdownLabel() {
        if (this.state.showPosted && this.state.showDraft) return "All Entries";
        if (this.state.showDraft && !this.state.showPosted) return "Draft Entries";
        return "Posted Entries";
    }

    get displayLines() {
        if (!this.state.hideZeroLines) return this.state.lines;
        return this.state.lines.filter((line) => {
            if (line.section_header) return true;
            const s = line.style || "data";
            if (s !== "data") return true;
            const current = (line.base_amount || 0) !== 0 || (line.vat_amount || 0) !== 0;
            if (current) return true;
            if (line.comparison_balances && line.comparison_balances.length) {
                return line.comparison_balances.some(
                    (cb) => (cb.base_amount || 0) !== 0 || (cb.vat_amount || 0) !== 0
                );
            }
            return false;
        });
    }

    openDateDropdown(ev) {
        ev.stopPropagation();
        this.state.dateDropdownOpen = !this.state.dateDropdownOpen;
    }

    setDateMode(mode) {
        this.state.dateMode = mode;
        this.state.dateDropdownOpen = false;
        this._loadData();
    }

    onMonthYearChange(ev) {
        this.state.monthYear = ev.target.value;
        this._loadData();
    }

    onCustomDateFromChange(ev) {
        this.state.customDateFrom = ev.target.value;
        this._loadData();
    }

    onCustomDateToChange(ev) {
        this.state.customDateTo = ev.target.value;
        this._loadData();
    }

    openOptionsDropdown(ev) {
        ev.stopPropagation();
        this.state.optionsDropdownOpen = !this.state.optionsDropdownOpen;
    }

    toggleShowPosted() {
        // Enterprise never allows both Posted and Draft to be unchecked at once.
        if (this.state.showPosted && !this.state.showDraft) return;
        this.state.showPosted = !this.state.showPosted;
        this._loadData();
    }

    toggleShowDraft() {
        if (this.state.showDraft && !this.state.showPosted) return;
        this.state.showDraft = !this.state.showDraft;
        this._loadData();
    }

    toggleHideZeroLines() {
        this.state.hideZeroLines = !this.state.hideZeroLines;
    }

    openComparisonDropdown(ev) {
        ev.stopPropagation();
        this.state.comparisonDropdownOpen = !this.state.comparisonDropdownOpen;
    }

    setComparisonMode(mode) {
        this.state.comparisonMode = mode;
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

    setPeriodOrder(order) {
        this.state.periodOrder = order;
    }

    dismissWarning() {
        this.state.showUnpostedWarning = false;
    }

    closeTaxReport() {
        window.history.back();
    }

    fmtNum(value) {
        const d = this.state.currencyDigits ?? 2;
        return fmtAmt(value, d);
    }

    fmtNumWithSym(value) {
        const d = this.state.currencyDigits ?? 2;
        const amt = fmtAmt(value, d);
        const sym = this.state.currencySymbol || this.state.currencyName || "";
        return sym ? `${amt} ${sym}` : amt;
    }

    async exportTaxPDF() {
        if (this.state.exportingPdf) return;
        this.state.exportingPdf = true;
        try {
            const range = this._getDateRange();
            const payload = {
                date_from: range.date_from,
                date_to: range.date_to,
                company_id: this.state.companyId,
                target_move: this.targetMoveValue,
                analytic_account_ids: this.state.analyticAccountIds,
            };
            if (this.state.comparisonMode !== "none") {
                const periods = this._getComparisonPeriods();
                if (periods && periods.length) {
                    payload.comparison_periods = periods;
                }
            }
            const result = await rpc("/fs_enterprise/export_tax_pdf", payload);
            if (result?.file_content) {
                const link = document.createElement("a");
                link.href = "data:application/pdf;base64," + result.file_content;
                link.download = result.file_name || "Tax_Report.pdf";
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            }
        } catch (e) {
            console.error("Tax PDF export error:", e);
            this.notification.add("PDF export failed. Please try again.", { type: "danger" });
        } finally {
            this.state.exportingPdf = false;
        }
    }

    async exportTaxExcel() {
        if (this.state.exportingXlsx) return;
        this.state.exportingXlsx = true;
        try {
            const range = this._getDateRange();
            const payload = {
                date_from: range.date_from,
                date_to: range.date_to,
                company_id: this.state.companyId,
                target_move: this.targetMoveValue,
                analytic_account_ids: this.state.analyticAccountIds,
            };
            if (this.state.comparisonMode !== "none") {
                const periods = this._getComparisonPeriods();
                if (periods && periods.length) {
                    payload.comparison_periods = periods;
                }
            }
            const result = await rpc("/fs_enterprise/export_tax_xlsx", payload);
            if (result?.file_content) {
                const link = document.createElement("a");
                link.href = "data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64," + result.file_content;
                link.download = result.file_name || "Tax_Report.xlsx";
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            }
        } catch (e) {
            console.error("Tax Excel export error:", e);
            this.notification.add("Excel export failed. Please try again.", { type: "danger" });
        } finally {
            this.state.exportingXlsx = false;
        }
    }

    isDataLine(line) {
        return !line.section_header;
    }

    getComparisonPeriodForColumn(line, colIndex) {
        const ordered = this.orderedComparisonColumns;
        if (!ordered.length || !line.comparison_balances) {
            return null;
        }
        const col = ordered[colIndex];
        if (!col) return null;
        return line.comparison_balances.find(
            (cb) => cb.label === col.label && cb.date_to === col.date_to
        );
    }

    onClickAmount(line, type, customDates = null) {
        if (!line.tax_ids || !line.tax_ids.length) {
            return;
        }

        let dateFrom, dateTo;
        if (customDates) {
            dateFrom = customDates.date_from;
            dateTo = customDates.date_to;
        } else {
            const range = this._getDateRange();
            dateFrom = range.date_from;
            dateTo = range.date_to;
        }

        const domain = [
            ["company_id", "=", this.state.companyId],
            ["display_type", "not in", ["line_section", "line_note"]],
            ["date", ">=", dateFrom],
            ["date", "<=", dateTo],
        ];

        const targetMove = this.targetMoveValue;
        // FIX: use parent_state like backend
        if (targetMove === "posted") {
            domain.push(["parent_state", "=", "posted"]);
        } else if (targetMove === "draft") {
            domain.push(["parent_state", "=", "draft"]);
        } else {
            domain.push(["parent_state", "!=", "cancel"]);
        }

        if (type === "base") {
            domain.push(["tax_ids", "in", line.tax_ids]);
        } else {
            domain.push(["tax_line_id", "in", line.tax_ids]);
        }
        if (this.state.analyticAccountIds && this.state.analyticAccountIds.length) {
            domain.push(["analytic_distribution", "in", this.state.analyticAccountIds]);
        }

        this.action.doAction({
            type: "ir.actions.act_window",
            name: `${line.name} (${type === 'base' ? 'Base' : 'Tax'} Items)`,
            res_model: "account.move.line",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: domain,
            target: "current",
        });
    }

    taxRowClass(line) {
        if (line.section_header) return "tax-ent-section-header";
        const s = line.style || "data";
        if (s === "total") return "tax-ent-row tax-ent-total";
        if (s === "subtotal") return "tax-ent-row tax-ent-subtotal";
        if (s === "summary") return "tax-ent-row tax-ent-summary";
        return "tax-ent-row tax-ent-data";
    }

    toggleTheme(ev) {
        if (ev) ev.stopPropagation();
        this.state.theme = this.state.theme === "dark" ? "light" : "dark";
        localStorage.setItem("fs_ent_theme", this.state.theme);
    }
}

registry
    .category("actions")
    .add("fs_enterprise.TaxReportView", TaxReportView);