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

// ---------------------------------------------------------------------------
// Utility helpers
// ---------------------------------------------------------------------------

/** Format a number as a monetary string (no symbol) */
function fmtAmt(value, decimals = 2) {
    if (value === null || value === undefined) return "0.00";
    return Number(value).toLocaleString(undefined, {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
    });
}

/** Get the first day of the current year as ISO string */
function defaultDateFrom() {
    const d = new Date();
    return `${d.getFullYear()}-01-01`;
}

/** Get today as ISO string */
function defaultDateTo() {
    return new Date().toISOString().slice(0, 10);
}

/** Format ISO date string for display (e.g. "13/07/2026") */
function displayDate(isoStr) {
    if (!isoStr) return "";
    const [y, m, d] = isoStr.split("-");
    return `${d}/${m}/${y}`;
}

function isoDate(d) {
    return d.toISOString().slice(0, 10);
}

function getMonthRange(date) {
    const y = date.getFullYear();
    const m = date.getMonth();
    return {
        from: isoDate(new Date(y, m, 1)),
        to: isoDate(new Date(y, m + 1, 0)),
    };
}

function getQuarterRange(date) {
    const y = date.getFullYear();
    const q = Math.floor(date.getMonth() / 3);
    return {
        from: isoDate(new Date(y, q * 3, 1)),
        to: isoDate(new Date(y, q * 3 + 3, 0)),
    };
}

function getFiscalYearRange(date) {
    const y = date.getFullYear();
    return { from: `${y}-01-01`, to: `${y}-12-31` };
}

function shortMonth(d) {
    return d.toLocaleString("en-US", { month: "short" });
}

function longMonthLabel(d) {
    return d.toLocaleString("en-US", { month: "long", year: "numeric" });
}

function quarterLabel(fromIso, toIso) {
    const from = new Date(fromIso);
    const to = new Date(toIso);
    if (from.getFullYear() === to.getFullYear()) {
        return `${shortMonth(from)} - ${shortMonth(to)} ${from.getFullYear()}`;
    }
    return `${shortMonth(from)} ${from.getFullYear()} - ${shortMonth(to)} ${to.getFullYear()}`;
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export class GeneralLedgerView extends Component {
    static template = "oca_gl.GeneralLedgerView";
    static props = ["*"];

    setup() {
        // rpc is a direct import in Odoo 17+, not a service
        this.action = useService("action");
        this.notification = useService("notification");

        // -------------------------------------------------------------------
        // Reactive state
        // -------------------------------------------------------------------
        this.state = useState({
            // Data
            accounts: [],
            grandTotals: { debit: 0, credit: 0, balance: 0 },
            currencyName: "",
            currencySymbol: "",
            companyName: "",
            loading: false,
            error: null,

            // Expand/collapse
            expandedAccounts: new Set(),

            // Filters
            dateFrom: defaultDateFrom(),
            dateTo: defaultDateTo(),
            targetMove: "posted",       // 'posted' | 'all'
            hideAccountAt0: false,
            groupedBy: "none",          // 'none' | 'partners' | 'taxes'

            // Period select: 'custom' | 'month' | 'quarter' | 'fiscal_year'
            periodMode: "custom",
            periodDropdownOpen: false,
            monthRef: isoDate(new Date()),
            quarterRef: isoDate(new Date()),
            fiscalYearRef: isoDate(new Date()),

            // Journal multi-select
            allJournals: [],            // [{id, name, code}]
            selectedJournalIds: [],
            journalDropdownOpen: false,
            journalSearch: "",

            // Company
            companies: [],
            companyId: null,

            // Export loading
            exportingPdf: false,
            exportingXlsx: false,

            // Report Type: 'gl' (General Ledger) or 'tb' (Trial Balance)
            reportType: this.props.action?.params?.default_report_type || "gl",

            // Trial Balance per-row "⋮" menu (drill-down to General Ledger)
            tbRowMenuOpenId: null,
            drilldownBreadcrumb: false,

            // Search
            searchQuery: "",

            // Comparison state
            comparisonMode: "none", // 'none' | 'previous_period' | 'same_period_last_year' | 'custom'
            comparisonPeriodCount: 1,
            comparisonDateFrom: defaultDateFrom(),
            comparisonDateTo: defaultDateTo(),
            comparisonDropdownOpen: false,

            // Optional dropdown menu for filters & columns
            optionsDropdownOpen: false,

            // Optional column visibility
            showComm: false,
            showCurrency: false,
        });

        // Refs for click-outside handling
        this.journalDropdownRef = useRef("journalDropdownRef");
        this.optionsDropdownRef = useRef("optionsDropdownRef");
        this.comparisonDropdownRef = useRef("comparisonDropdownRef");
        this.periodDropdownRef = useRef("periodDropdownRef");

        // -------------------------------------------------------------------
        // Lifecycle
        // -------------------------------------------------------------------
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

    // -------------------------------------------------------------------
    // Lifecycle cleanup (manual; OWL 2 uses willUnmount if declared)
    // -------------------------------------------------------------------
    _onDocClick(ev) {
        // Close journal dropdown when clicking outside
        if (this.state.journalDropdownOpen) {
            const el = this.journalDropdownRef.el;
            if (el && !el.contains(ev.target)) {
                this.state.journalDropdownOpen = false;
            }
        }
        // Close options dropdown when clicking outside
        if (this.state.optionsDropdownOpen) {
            const el = this.optionsDropdownRef.el;
            if (el && !el.contains(ev.target)) {
                this.state.optionsDropdownOpen = false;
            }
        }
        // Close comparison dropdown when clicking outside
        if (this.state.comparisonDropdownOpen) {
            const el = this.comparisonDropdownRef.el;
            if (el && !el.contains(ev.target)) {
                this.state.comparisonDropdownOpen = false;
            }
        }
        // Close period dropdown when clicking outside
        if (this.state.periodDropdownOpen) {
            const el = this.periodDropdownRef.el;
            if (el && !el.contains(ev.target)) {
                this.state.periodDropdownOpen = false;
            }
        }
        // Close Trial Balance row "⋮" menu when clicking outside it
        if (this.state.tbRowMenuOpenId !== null) {
            if (!ev.target.closest(".oca-tb-row-menu")) {
                this.state.tbRowMenuOpenId = null;
            }
        }
    }

    // -------------------------------------------------------------------
    // Data loading
    // -------------------------------------------------------------------

    async _loadInitData() {
        try {
            const result = await rpc("/oca_gl/init", {
                company_id: this.state.companyId,
            });
            this.state.allJournals = result.journals || [];
            this.state.companies = result.companies || [];
            this.state.companyId = result.company_id;
            this.state.companyName = result.company_name;
            this.state.currencyName = result.currency_name;
            this.state.currencySymbol = result.currency_symbol;
            if (!this.state.dateFrom) this.state.dateFrom = result.date_from;
            if (!this.state.dateTo) this.state.dateTo = result.date_to;
        } catch (e) {
            console.error("GL init error:", e);
        }
    }

    async _loadData() {
        this.state.loading = true;
        this.state.error = null;
        try {
            // 1. Fetch current period data
            const result = await rpc("/oca_gl/get_data", {
                date_from: this.state.dateFrom,
                date_to: this.state.dateTo,
                company_id: this.state.companyId,
                journal_ids: this.state.selectedJournalIds.length
                    ? this.state.selectedJournalIds
                    : null,
                target_move: this.state.targetMove,
                hide_account_at_0: this.state.hideAccountAt0,
                grouped_by: this.state.groupedBy,
            });

            const currentAccounts = result.accounts || [];

            // 2. Fetch comparison period data if active
            let compAccounts = [];
            const compDates = this.getComparisonDates();
            if (compDates) {
                try {
                    const compResult = await rpc("/oca_gl/get_data", {
                        date_from: compDates.date_from,
                        date_to: compDates.date_to,
                        company_id: this.state.companyId,
                        journal_ids: this.state.selectedJournalIds.length
                            ? this.state.selectedJournalIds
                            : null,
                        target_move: this.state.targetMove,
                        hide_account_at_0: this.state.hideAccountAt0,
                        grouped_by: this.state.groupedBy,
                    });
                    compAccounts = compResult.accounts || [];
                } catch (err) {
                    console.error("Comparison load error:", err);
                }
            }

            const compMap = new Map(compAccounts.map((a) => [a.id, a]));

            // 3. Merge comparison data into main accounts
            this.state.accounts = currentAccounts.map((acc) => {
                const compAcc = compMap.get(acc.id);
                acc.comparison_fin_bal = compAcc
                    ? compAcc.fin_bal
                    : { debit: 0, credit: 0, balance: 0 };
                return acc;
            });

            this.state.currencyName = result.currency_name || this.state.currencyName;
            this.state.currencySymbol = result.currency_symbol || this.state.currencySymbol;
            this.state.companyName = result.company_name || this.state.companyName;

            // Compute grand totals
            let gDebit = 0, gCredit = 0, gBalance = 0, gInitBal = 0;
            let gCompDebit = 0, gCompCredit = 0, gCompBalance = 0;

            for (const acc of this.state.accounts) {
                gDebit += acc.fin_bal.debit;
                gCredit += acc.fin_bal.credit;
                gBalance += acc.fin_bal.balance;
                gInitBal += acc.init_bal.balance;

                if (acc.comparison_fin_bal) {
                    gCompDebit += acc.comparison_fin_bal.debit;
                    gCompCredit += acc.comparison_fin_bal.credit;
                    gCompBalance += acc.comparison_fin_bal.balance;
                }
            }

            this.state.grandTotals = {
                debit: gDebit,
                credit: gCredit,
                balance: gBalance,
                initBalance: gInitBal,
                compDebit: gCompDebit,
                compCredit: gCompCredit,
                compBalance: gCompBalance,
            };

            // Preserve expanded state across reloads
            // (no change needed; Set persists)
        } catch (e) {
            console.error("GL data error:", e);
            this.state.error = "Failed to load General Ledger data. Please check the console for details.";
        } finally {
            this.state.loading = false;
        }
    }

    // -------------------------------------------------------------------
    // Filter handlers
    // -------------------------------------------------------------------

    onDateFromChange(ev) {
        this.state.dateFrom = ev.target.value;
        this._loadData();
    }

    onDateToChange(ev) {
        this.state.dateTo = ev.target.value;
        this._loadData();
    }

    // -------------------------------------------------------------------
    // Period select (Month / Quarter / Fiscal Year, each independently
    // navigable with prev/next arrows; used by both GL and TB)
    // -------------------------------------------------------------------

    openPeriodDropdown(ev) {
        ev.stopPropagation();
        this.state.periodDropdownOpen = !this.state.periodDropdownOpen;
    }

    _rangeForType(type) {
        if (type === "month") return getMonthRange(new Date(this.state.monthRef));
        if (type === "quarter") return getQuarterRange(new Date(this.state.quarterRef));
        return getFiscalYearRange(new Date(this.state.fiscalYearRef));
    }

    _applyPeriod(type) {
        const range = this._rangeForType(type);
        this.state.periodMode = type === "fiscal_year" ? "fiscal_year" : type;
        this.state.dateFrom = range.from;
        this.state.dateTo = range.to;
        this._loadData();
    }

    /** Row label clicked: apply whatever period that row currently shows, close dropdown */
    selectPeriod(type) {
        this._applyPeriod(type);
        this.state.periodDropdownOpen = false;
    }

    /** Arrow clicked: step that row's reference date, then apply + keep dropdown open */
    navigatePeriod(type, delta, ev) {
        if (ev) ev.stopPropagation();
        const refKey = type === "fiscal_year" ? "fiscalYearRef" : `${type}Ref`;
        const d = new Date(this.state[refKey]);
        if (type === "month") d.setMonth(d.getMonth() + delta);
        else if (type === "quarter") d.setMonth(d.getMonth() + delta * 3);
        else d.setFullYear(d.getFullYear() + delta);
        this.state[refKey] = isoDate(d);
        this._applyPeriod(type);
    }

    enableCustomPeriod() {
        this.state.periodMode = "custom";
    }

    get periodPillLabel() {
        if (this.state.periodMode === "month") {
            return longMonthLabel(new Date(this.state.monthRef));
        }
        if (this.state.periodMode === "quarter") {
            const r = getQuarterRange(new Date(this.state.quarterRef));
            return quarterLabel(r.from, r.to);
        }
        if (this.state.periodMode === "fiscal_year") {
            return String(new Date(this.state.fiscalYearRef).getFullYear());
        }
        return this.dateRangeLabel;
    }

    get currentMonthLabel() {
        return longMonthLabel(new Date(this.state.monthRef));
    }

    get currentQuarterLabel() {
        const r = getQuarterRange(new Date(this.state.quarterRef));
        return quarterLabel(r.from, r.to);
    }

    get currentFiscalYearLabel() {
        return String(new Date(this.state.fiscalYearRef).getFullYear());
    }

    toggleTargetMove() {
        this.state.targetMove = this.state.targetMove === "posted" ? "all" : "posted";
        this._loadData();
    }

    setTargetMove(mode) {
        if (this.state.targetMove !== mode) {
            this.state.targetMove = mode;
            this._loadData();
        }
    }

    setReportType(type) {
        this.state.reportType = type;
        this.state.drilldownBreadcrumb = false;
    }

    // -------------------------------------------------------------------
    // Trial Balance row "⋮" menu → drill down into General Ledger
    // -------------------------------------------------------------------

    toggleTbRowMenu(accountId, ev) {
        if (ev) ev.stopPropagation();
        this.state.tbRowMenuOpenId =
            this.state.tbRowMenuOpenId === accountId ? null : accountId;
    }

    drillToGeneralLedger(account, ev) {
        if (ev) ev.stopPropagation();
        this.state.tbRowMenuOpenId = null;
        this.state.drilldownBreadcrumb = true;
        this.state.reportType = "gl";
        this.state.searchQuery = account.code || account.name || "";
        this.state.expandedAccounts = new Set([account.id]);
    }

    backToTrialBalance(ev) {
        if (ev) ev.preventDefault();
        this.state.reportType = "tb";
        this.state.searchQuery = "";
        this.state.drilldownBreadcrumb = false;
    }

    openOptionsDropdown(ev) {
        ev.stopPropagation();
        this.state.optionsDropdownOpen = !this.state.optionsDropdownOpen;
    }

    openComparisonDropdown(ev) {
        ev.stopPropagation();
        this.state.comparisonDropdownOpen = !this.state.comparisonDropdownOpen;
    }

    setComparisonMode(mode) {
        this.state.comparisonMode = mode;
        this._loadData();
    }

    onComparisonPeriodCountChange(ev) {
        const v = parseInt(ev.target.value, 10);
        this.state.comparisonPeriodCount = !v || v < 1 ? 1 : v;
        if (this.state.comparisonMode === "previous_period") {
            this._loadData();
        }
    }

    onComparisonDateFromChange(ev) {
        this.state.comparisonDateFrom = ev.target.value;
        this._loadData();
    }

    onComparisonDateToChange(ev) {
        this.state.comparisonDateTo = ev.target.value;
        this._loadData();
    }

    getComparisonDates() {
        if (!this.state.dateFrom || !this.state.dateTo) return null;
        const dFrom = new Date(this.state.dateFrom);
        const dTo = new Date(this.state.dateTo);

        if (this.state.comparisonMode === "previous_period") {
            const diffTime = Math.abs(dTo - dFrom);
            const diffDays =
                (Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1) *
                (this.state.comparisonPeriodCount || 1);
            const compFrom = new Date(dFrom);
            compFrom.setDate(compFrom.getDate() - diffDays);
            const compTo = new Date(dTo);
            compTo.setDate(compTo.getDate() - diffDays);
            return {
                date_from: compFrom.toISOString().slice(0, 10),
                date_to: compTo.toISOString().slice(0, 10),
            };
        } else if (this.state.comparisonMode === "same_period_last_year") {
            const compFrom = new Date(dFrom);
            compFrom.setFullYear(compFrom.getFullYear() - 1);
            const compTo = new Date(dTo);
            compTo.setFullYear(compTo.getFullYear() - 1);
            return {
                date_from: compFrom.toISOString().slice(0, 10),
                date_to: compTo.toISOString().slice(0, 10),
            };
        } else if (this.state.comparisonMode === "custom") {
            return {
                date_from: this.state.comparisonDateFrom || defaultDateFrom(),
                date_to: this.state.comparisonDateTo || defaultDateTo(),
            };
        }
        return null;
    }

    toggleHideAtZero() {
        this.state.hideAccountAt0 = !this.state.hideAccountAt0;
        this._loadData();
    }

    // Journal dropdown
    openJournalDropdown(ev) {
        ev.stopPropagation();
        this.state.journalDropdownOpen = !this.state.journalDropdownOpen;
    }

    onJournalSearch(ev) {
        this.state.journalSearch = ev.target.value;
    }

    toggleJournal(journalId) {
        const idx = this.state.selectedJournalIds.indexOf(journalId);
        if (idx === -1) {
            this.state.selectedJournalIds.push(journalId);
        } else {
            this.state.selectedJournalIds.splice(idx, 1);
        }
        this._loadData();
    }

    clearJournals() {
        this.state.selectedJournalIds = [];
        this._loadData();
    }

    // -------------------------------------------------------------------
    // Search Handler
    // -------------------------------------------------------------------

    onSearchInput(ev) {
        this.state.searchQuery = ev.target.value;
    }

    clearSearch() {
        this.state.searchQuery = "";
    }

    // -------------------------------------------------------------------
    // Optional columns
    // -------------------------------------------------------------------

    toggleShowComm() {
        this.state.showComm = !this.state.showComm;
    }

    toggleShowCurrency() {
        this.state.showCurrency = !this.state.showCurrency;
    }

    // -------------------------------------------------------------------
    // Expand / Collapse
    // -------------------------------------------------------------------

    toggleAccount(accountId) {
        if (this.state.expandedAccounts.has(accountId)) {
            this.state.expandedAccounts.delete(accountId);
        } else {
            this.state.expandedAccounts.add(accountId);
        }
    }

    expandAll() {
        for (const acc of this.state.accounts) {
            this.state.expandedAccounts.add(acc.id);
        }
    }

    collapseAll() {
        this.state.expandedAccounts.clear();
    }

    isExpanded(accountId) {
        return this.state.expandedAccounts.has(accountId);
    }

    // -------------------------------------------------------------------
    // Navigation: open move form
    // -------------------------------------------------------------------

    openMove(moveId) {
        if (!moveId) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "account.move",
            res_id: moveId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openMoveLine(lineId) {
        if (!lineId) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "account.move.line",
            res_id: lineId,
            views: [[false, "form"]],
            target: "new",
        });
    }

    /** Opens the "Journal Items" list for a given account, scoped to the
     * current date range, posted/draft filter, and company — mirrors the
     * native Odoo Enterprise smart button (Image 3). */
    openJournalItems(account, ev) {
        if (ev) ev.stopPropagation();
        if (!account) return;
        const domain = [["account_id", "=", account.id]];
        if (this.state.dateFrom) domain.push(["date", ">=", this.state.dateFrom]);
        if (this.state.dateTo) domain.push(["date", "<=", this.state.dateTo]);
        if (this.state.targetMove === "posted") {
            domain.push(["parent_state", "=", "posted"]);
        }
        if (this.state.companyId) {
            domain.push(["company_id", "=", this.state.companyId]);
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            name: `Journal Items — ${account.code ? account.code + " " : ""}${account.name || ""}`.trim(),
            res_model: "account.move.line",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            view_mode: "list,form",
            domain,
            context: { search_default_posted: this.state.targetMove === "posted" },
            target: "current",
        });
    }

    // -------------------------------------------------------------------
    // Export
    // -------------------------------------------------------------------

    get _exportFilters() {
        return {
            date_from: this.state.dateFrom,
            date_to: this.state.dateTo,
            company_id: this.state.companyId,
            journal_ids: this.state.selectedJournalIds.length
                ? this.state.selectedJournalIds
                : null,
            target_move: this.state.targetMove,
            hide_account_at_0: this.state.hideAccountAt0,
            grouped_by: this.state.groupedBy,
            report_type: this.state.reportType,
        };
    }

    async exportPDF() {
        if (this.state.exportingPdf) return;
        this.state.exportingPdf = true;
        try {
            const reportAction = await rpc("/oca_gl/export", {
                export_format: "pdf",
                filters: this._exportFilters,
            });
            await this.action.doAction(reportAction);
        } catch (e) {
            console.error("PDF export error:", e);
            this.notification.add("PDF export failed. Please try again.", {
                type: "danger",
            });
        } finally {
            this.state.exportingPdf = false;
        }
    }

    async exportXLSX() {
        if (this.state.exportingXlsx) return;
        this.state.exportingXlsx = true;
        try {
            const reportAction = await rpc("/oca_gl/export", {
                export_format: "xlsx",
                filters: this._exportFilters,
            });
            await this.action.doAction(reportAction);
        } catch (e) {
            console.error("XLSX export error:", e);
            this.notification.add("XLSX export failed. Please try again.", {
                type: "danger",
            });
        } finally {
            this.state.exportingXlsx = false;
        }
    }

    // -------------------------------------------------------------------
    // Computed helpers for template
    // -------------------------------------------------------------------

    /** Formatted currency amount with symbol */
    fmt(value) {
        return `${fmtAmt(value)} ${this.state.currencyName}`;
    }

    /** Formatted amount without currency */
    fmtNum(value) {
        return fmtAmt(value);
    }

    /** Formatted amount with currency symbol inline (e.g. 1,725.00 SR) */
    fmtNumWithSym(value) {
        const amt = fmtAmt(value);
        const sym = this.state.currencySymbol || this.state.currencyName || "";
        return sym ? `${amt} ${sym}` : amt;
    }

    /** CSS class for balance cell */
    balanceClass(value) {
        const n = Number(value) || 0;
        if (n > 0.005) return "oca-gl-balance-pos";
        if (n < -0.005) return "oca-gl-balance-neg";
        return "oca-gl-balance-zero";
    }

    /** Label for options dropdown button */
    get optionsDropdownLabel() {
        const mode = this.state.targetMove === "posted" ? "Posted Entries" : "Draft & Posted Entries";
        return mode;
    }

    /** Label for journal filter pill */
    get journalPillLabel() {
        const sel = this.state.selectedJournalIds;
        if (!sel.length) return "All Journals";
        if (sel.length === 1) {
            const j = this.state.allJournals.find((j) => j.id === sel[0]);
            return j ? j.name : "1 Journal";
        }
        return `${sel.length} Journals`;
    }

    /** Filtered journals for dropdown search */
    get filteredJournals() {
        const q = (this.state.journalSearch || "").toLowerCase();
        if (!q) return this.state.allJournals;
        return this.state.allJournals.filter(
            (j) =>
                j.name.toLowerCase().includes(q) ||
                j.code.toLowerCase().includes(q)
        );
    }

    /** Display date range label */
    get dateRangeLabel() {
        const f = displayDate(this.state.dateFrom);
        const t = displayDate(this.state.dateTo);
        if (!f && !t) return "All Dates";
        return `${f} → ${t}`;
    }

    /** true if any account is expanded */
    get anyExpanded() {
        return this.state.expandedAccounts.size > 0;
    }

    /** Count of visible accounts */
    get dateRangeShortLabel() {
        if (!this.state.dateFrom && !this.state.dateTo) return "Period";
        const f = displayDate(this.state.dateFrom);
        const t = displayDate(this.state.dateTo);
        return `${f} - ${t}`;
    }

    get comparisonRangeLabel() {
        const dates = this.getComparisonDates();
        if (!dates) return "Comparison Period";
        const f = displayDate(dates.date_from);
        const t = displayDate(dates.date_to);
        return `${f} - ${t}`;
    }

    get comparisonModeLabel() {
        if (this.state.comparisonMode === "none") return "Comparison";
        if (this.state.comparisonMode === "previous_period") {
            return this.state.comparisonPeriodCount > 1
                ? `Previous ${this.state.comparisonPeriodCount} Periods`
                : "Previous Period";
        }
        if (this.state.comparisonMode === "same_period_last_year") return "Same Period Last Year";
        return "Custom Dates";
    }

    get accountCount() {
        return this.displayedAccounts.length;
    }

    get displayedAccounts() {
        const q = (this.state.searchQuery || "").trim().toLowerCase();
        if (!q) return this.state.accounts;
        return this.state.accounts.filter((acc) => {
            const codeMatch = (acc.code || "").toLowerCase().includes(q);
            const nameMatch = (acc.name || "").toLowerCase().includes(q);
            if (codeMatch || nameMatch) return true;
            return (acc.move_lines || []).some(
                (line) =>
                    (line.move_name || "").toLowerCase().includes(q) ||
                    (line.ref_label || "").toLowerCase().includes(q) ||
                    (line.partner || "").toLowerCase().includes(q)
            );
        });
    }

    get accountColspan() {
        let span = 3;
        if (this.state.showComm) span++;
        if (this.state.showCurrency) span++;
        return span;
    }
}

// Register as client action
registry
    .category("actions")
    .add("oca_gl.GeneralLedgerView", GeneralLedgerView);