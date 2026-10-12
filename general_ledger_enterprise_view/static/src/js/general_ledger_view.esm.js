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
import { download } from "@web/core/network/download";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

// Partner sub-rows fetched per account (the rest via "Load more partners").
const PARTNER_PAGE_SIZE = 200;
// true  -> exports are real binary downloads (/gl_enterprise/export_file).
// false -> previous behaviour (base64 inside JSON-RPC); safety switch.
const USE_HTTP_DOWNLOAD = true;

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

/** Get today (LOCAL date) as ISO string */
function defaultDateTo() {
    return isoDate(new Date());
}

/** Format ISO date string for display (e.g. "13/07/2026") */
function displayDate(isoStr) {
    if (!isoStr) return "";
    const [y, m, d] = isoStr.split("-");
    return `${d}/${m}/${y}`;
}

/**
 * Format a Date as YYYY-MM-DD using its LOCAL calendar fields.
 * toISOString() converts to UTC first, which shifts the date by one day in
 * zones ahead of UTC (e.g. India: local 00:00 is the previous day in UTC).
 */
function isoDate(d) {
    const mm = String(d.getMonth() + 1).padStart(2, "0");
    const dd = String(d.getDate()).padStart(2, "0");
    return `${d.getFullYear()}-${mm}-${dd}`;
}

/**
 * Parse "YYYY-MM-DD" as a LOCAL date (midnight local time).
 * new Date("YYYY-MM-DD") is parsed as UTC, which gives the previous day in
 * zones behind UTC (e.g. the Americas).
 */
function parseIsoDate(str) {
    const [y, m, d] = String(str || "").slice(0, 10).split("-").map(Number);
    if (!y || !m || !d) return new Date(NaN);
    return new Date(y, m - 1, d);
}

/** Same calendar day `years` years away; Feb 29 clamps to Feb 28. */
function shiftYears(d, years) {
    const r = new Date(d.getFullYear() + years, d.getMonth(), d.getDate());
    if (r.getMonth() !== d.getMonth()) {
        r.setDate(0); // overflowed into March -> last day of February
    }
    return r;
}

function getMonthRange(date) {
    const y = date.getFullYear();
    const m = date.getMonth();
    return {
        from: isoDate(new Date(y, m, 1)),
        to: isoDate(new Date(y, m + 1, 0)),
    };
}

/** Local-date ISO formatter (avoids the UTC shift of toISOString) */
function localIso(y, m, d) {
    const dt = new Date(y, m, d);
    const mm = String(dt.getMonth() + 1).padStart(2, "0");
    const dd = String(dt.getDate()).padStart(2, "0");
    return `${dt.getFullYear()}-${mm}-${dd}`;
}

function getQuarterRange(date) {
    const y = date.getFullYear();
    const q = Math.floor(date.getMonth() / 3);
    return {
        from: localIso(y, q * 3, 1),      // Jan 1 / Apr 1 / Jul 1 / Oct 1
        to: localIso(y, q * 3 + 3, 0),    // Mar 31 / Jun 30 / Sep 30 / Dec 31
    };
}

function getFiscalYearRange(date, fy) {
    const month = (fy && fy.month) || 1;
    const day = (fy && fy.day) || 1;
    // Start = latest FY start on/before `date`; end = day before the next start.
    let startYear = date.getFullYear();
    if (new Date(startYear, month - 1, day) > date) {
        startYear -= 1;
    }
    const start = new Date(startYear, month - 1, day);
    const end = new Date(startYear + 1, month - 1, day - 1);
    return { from: isoDate(start), to: isoDate(end) };
}

function shortMonth(d) {
    return d.toLocaleString("en-US", { month: "short" });
}

function longMonthLabel(d) {
    return d.toLocaleString("en-US", { month: "long", year: "numeric" });
}

function quarterLabel(fromIso, toIso) {
    const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const [fy, fm] = fromIso.split("-").map(Number);
    const [ty, tm] = toIso.split("-").map(Number);
    if (fy === ty) {
        return `${MONTHS[fm - 1]} - ${MONTHS[tm - 1]} ${fy}`;
    }
    return `${MONTHS[fm - 1]} ${fy} - ${MONTHS[tm - 1]} ${ty}`;
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export class GeneralLedgerView extends Component {
    static template = "gl_enterprise.GeneralLedgerView";
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
            grandTotals: { debit: 0, credit: 0, balance: 0, endingBalance: 0, initBalance: 0 },
            currencyName: "",
            currencySymbol: "",
            companyName: "",
            loading: false,
            error: null,

            // Expand/collapse
            expandedAccounts: new Set(),
            expandedPartners: new Set(),
            expandedJournals: new Set(),   // journal sub-group keys (GL, grouped_by=journals)

            // Filters
            dateFrom: defaultDateFrom(),
            dateTo: defaultDateTo(),
            targetMove: "posted",       // 'posted' | 'all'
            hideAccountAt0: true,       // Hide 0 lines: ON by default on every load
            groupedBy: "none",          // 'none' | 'journals' (partners are grouped automatically for trade accounts)

            // Period select: 'custom' | 'month' | 'quarter' | 'fiscal_year'
            periodMode: "custom",
            periodDropdownOpen: false,
            monthRef: isoDate(new Date()),
            quarterRef: isoDate(new Date()),
            fiscalYearRef: isoDate(new Date()),
            // Company fiscal-year start (from /gl_enterprise/init). Jan 1 until loaded.
            fyStartMonth: 1,
            fyStartDay: 1,

            // Journal multi-select
            allJournals: [],            // [{id, name, code}]
            selectedJournalIds: [],
            journalDropdownOpen: false,
            journalSearch: "",

            // Accounts multi-select — powers lazy loading. The GL/TB no
            // longer loads every account on open; the user either picks
            // specific accounts here or clicks "Load All".
            allAccounts: [],            // [{id, name, code}]
            selectedAccountIds: [],
            accountDropdownOpen: false,
            accountSearch: "",
            loadAllMode: false,         // true once the user clicks "Load All"

            // Analytic accounts multi-select
            allAnalyticAccounts: [],    // [{id, name, code}]
            selectedAnalyticIds: [],
            analyticDropdownOpen: false,
            analyticSearch: "",

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
            searchSuggestOpen: false,

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

            // Theme
            lightTheme: false,
        });

        // Refs for click-outside handling
        this.journalDropdownRef = useRef("journalDropdownRef");
        this.accountDropdownRef = useRef("accountDropdownRef");
        this.searchBoxRef = useRef("searchBoxRef");
        this.analyticDropdownRef = useRef("analyticDropdownRef");
        this.optionsDropdownRef = useRef("optionsDropdownRef");
        this.comparisonDropdownRef = useRef("comparisonDropdownRef");
        this.periodDropdownRef = useRef("periodDropdownRef");

        // FIX 1c: Stale-response guard.
        // Odoo JSON-RPC does not support AbortController, so we use a
        // monotonic sequence counter: every new _loadData() call increments
        // _loadSeq and captures its value. On completion the result is only
        // applied if the captured value still equals the current _loadSeq —
        // any older in-flight response is silently discarded.
        this._loadSeq = 0;
        // Debounce timer handle (cleared on unmount to prevent memory leaks).
        this._loadDebounceTimer = null;

        // Per-account lazy-loading state — reactive so the template re-renders
        // when loading/hasMore/lines change (spinner, Load More button).
        // linesState[key] = { lines: [], hasMore: false, lastId: 0, lastDate: null, loading: false }
        this._linesState = useState({});
        // Per-account "load more partners" state: { [accountId]: { loading } }
        this._partnerState = useState({});

        // -------------------------------------------------------------------
        // Lifecycle
        // -------------------------------------------------------------------
        onWillStart(async () => {
            await this._loadInitData();
            // NOTE: we deliberately do NOT call this._loadData() here.
            // Loading every account's move lines/balances on open is what
            // causes the initial lag. The view now opens empty; _loadData()
            // itself is guarded (see below) and only hits the server once
            // the user selects specific accounts or clicks "Load All".
        });

        this._docClickHandler = this._onDocClick.bind(this);
        onMounted(() => {
            document.addEventListener("click", this._docClickHandler);
        });
        onWillUnmount(() => {
            document.removeEventListener("click", this._docClickHandler);
            // Cancel any pending debounce timer so it cannot fire after unmount.
            if (this._loadDebounceTimer !== null) {
                clearTimeout(this._loadDebounceTimer);
                this._loadDebounceTimer = null;
            }
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
        // Close accounts dropdown when clicking outside
        if (this.state.accountDropdownOpen) {
            const el = this.accountDropdownRef.el;
            if (el && !el.contains(ev.target)) {
                this.state.accountDropdownOpen = false;
            }
        }
        // Close the search-box suggestion dropdown when clicking outside
        if (this.state.searchSuggestOpen) {
            const el = this.searchBoxRef.el;
            if (el && !el.contains(ev.target)) {
                this.state.searchSuggestOpen = false;
            }
        }
        // Close analytic dropdown when clicking outside
        if (this.state.analyticDropdownOpen) {
            const el = this.analyticDropdownRef.el;
            if (el && !el.contains(ev.target)) {
                this.state.analyticDropdownOpen = false;
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
            const result = await rpc("/gl_enterprise/init", {
                company_id: this.state.companyId,
            });
            this.state.allJournals = result.journals || [];
            this.state.allAnalyticAccounts = result.analytic_accounts || [];
            this.state.allAccounts = result.accounts || [];
            this.state.companies = result.companies || [];
            this.state.companyId = result.company_id;
            this.state.companyName = result.company_name;
            this.state.currencyName = result.currency_name;
            this.state.currencySymbol = result.currency_symbol;
            // Company fiscal year (e.g. April-March) instead of hardcoded Jan-Dec.
            if (result.fiscalyear_start_month) {
                this.state.fyStartMonth = result.fiscalyear_start_month;
                this.state.fyStartDay = result.fiscalyear_start_day || 1;
            }
            // This runs once in onWillStart, before the user can touch any
            // filter, so the server's fiscal-year range replaces the Jan-1 guess.
            this._serverDateFrom = result.date_from || null;
            this._serverDateTo = result.date_to || null;
            if (result.date_from) {
                this.state.dateFrom = result.date_from;
                this.state.comparisonDateFrom = result.date_from;
            }
            if (result.date_to) {
                this.state.dateTo = result.date_to;
                this.state.comparisonDateTo = result.date_to;
            }
        } catch (e) {
            console.error("GL init error:", e);
        }
    }

    // -------------------------------------------------------------------
    // Data loading — debounced + stale-response safe
    // -------------------------------------------------------------------

    /**
     * Debounced entry point used by all filter handlers.
     * Coalesces rapid successive calls (e.g. typing a date range, toggling
     * journals) into a single server request after 200 ms of idle time.
     * Safe to call multiple times in quick succession.
     */
    _loadData() {
        if (this._loadDebounceTimer !== null) {
            clearTimeout(this._loadDebounceTimer);
        }
        this._loadDebounceTimer = setTimeout(() => {
            this._loadDebounceTimer = null;
            this._doLoadData();
        }, 200);
    }

    /**
     * Actual data-fetching implementation, called by _loadData after debounce.
     * Uses _loadSeq to detect and discard stale responses (Fix 1c).
     */
    async _doLoadData() {
        // Lazy-load guard: until the user selects specific accounts or
        // explicitly requests "Load All", don't hit the server at all.
        // This is what fixes the multi-second lag on opening the GL —
        // the view simply stays empty (see noAccountsSelectedYet in the
        // template) until the user tells us what to fetch.
        if (this.noAccountsSelectedYet) {
            this.state.accounts = [];
            this.state.grandTotals = { debit: 0, credit: 0, balance: 0, endingBalance: 0, initBalance: 0 };
            this.state.loading = false;
            this.state.error = null;
            return;
        }

        // FIX 1c: Increment sequence counter and capture this call's token.
        // Any response that arrives with a different token is stale and dropped.
        const mySeq = ++this._loadSeq;
        this._expandSeq = (this._expandSeq || 0) + 1; // cancel stale line loads

        // Scope the query to the selected accounts, unless the user chose
        // "Load All" — in that case account_ids stays null/undefined and
        // the backend returns every account, same as before.
        const accountIdsFilter =
            !this.state.loadAllMode && this.state.selectedAccountIds.length
                ? this.state.selectedAccountIds
                : null;

        // Reset per-account lines state when filters change, so stale
        // lines from a previous query are not shown for the new filters.
        // BUG FIX: Can't reassign the useState object reference; clear keys in-place.
        for (const key of Object.keys(this._linesState)) {
            delete this._linesState[key];
        }
        for (const key of Object.keys(this._partnerState)) {
            delete this._partnerState[key];
        }
        // Also clear move_lines from all account objects so the template
        // shows the loading state instead of old data.
        for (const acc of this.state.accounts) {
            acc.move_lines = [];
        }

        this.state.loading = true;
        this.state.error = null;
        try {
            // 1. Fetch current period data
            const result = await rpc("/gl_enterprise/get_data", {
                date_from: this.state.dateFrom,
                date_to: this.state.dateTo,
                company_id: this.state.companyId,
                journal_ids: this.state.selectedJournalIds.length
                    ? this.state.selectedJournalIds
                    : null,
                account_ids: accountIdsFilter,
                analytic_ids: this.state.selectedAnalyticIds.length
                    ? this.state.selectedAnalyticIds
                    : null,
                target_move: this.state.targetMove,
                hide_account_at_0: this.state.hideAccountAt0,
                grouped_by: this.state.groupedBy,
                report_type: this.state.reportType,
                include_lines: false,
                // Partner paging is skipped while a comparison is active so
                // the comparison columns always line up with the same partners.
                partner_limit: this.getComparisonDates() ? null : PARTNER_PAGE_SIZE,
            });

            // FIX 1c: Stale-response check — discard if a newer request has started
            if (mySeq !== this._loadSeq) {
                return;
            }

            const currentAccounts = result.accounts || [];

            // 2. Fetch comparison period data if active
            let compAccounts = [];
            const compDates = this.getComparisonDates();
            if (compDates) {
                try {
                    const compResult = await rpc("/gl_enterprise/get_data", {
                        date_from: compDates.date_from,
                        date_to: compDates.date_to,
                        company_id: this.state.companyId,
                        journal_ids: this.state.selectedJournalIds.length
                            ? this.state.selectedJournalIds
                            : null,
                        account_ids: accountIdsFilter,
                        analytic_ids: this.state.selectedAnalyticIds.length
                            ? this.state.selectedAnalyticIds
                            : null,
                        target_move: this.state.targetMove,
                        hide_account_at_0: this.state.hideAccountAt0,
                        grouped_by: this.state.groupedBy,
                        report_type: this.state.reportType,
                        include_lines: false,
                    });
                    // Stale check for comparison request too
                    if (mySeq !== this._loadSeq) {
                        return;
                    }
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
                if (acc.has_partners && acc.partner_groups) {
                    const compPartnerMap = new Map(
                        (compAcc?.partner_groups || []).map((p) => [p.partner_id, p])
                    );
                    for (const pg of acc.partner_groups) {
                        const compPg = compPartnerMap.get(pg.partner_id);
                        pg.comparison_fin_bal = compPg
                            ? compPg.fin_bal
                            : { debit: 0, credit: 0, balance: 0, ending_balance: 0 };
                    }
                }
                return acc;
            });

            this.state.currencyName = result.currency_name || this.state.currencyName;
            this.state.currencySymbol = result.currency_symbol || this.state.currencySymbol;
            this.state.companyName = result.company_name || this.state.companyName;

            // Compute grand totals
            let gDebit = 0, gCredit = 0, gBalance = 0, gInitBal = 0, gEndBalance = 0;
            let gCompDebit = 0, gCompCredit = 0, gCompBalance = 0;

            for (const acc of this.state.accounts) {
                gDebit += acc.fin_bal.debit;
                gCredit += acc.fin_bal.credit;
                gBalance += acc.fin_bal.balance;
                gInitBal += acc.init_bal.balance;
                // TB "End Balance" = opening + period movement (ending_balance)
                gEndBalance += this.accountEndBalance(acc);

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
                endingBalance: gEndBalance,
                initBalance: gInitBal,
                compDebit: gCompDebit,
                compCredit: gCompCredit,
                compBalance: gCompBalance,
            };

            // Expanded sets survive a reload but the lines were cleared above:
            // fetch them again so unfolded rows are not empty.
            this._loadExpandedLines();
        } catch (e) {
            // FIX 1c: Only show errors from the latest request
            if (mySeq !== this._loadSeq) {
                return;
            }
            console.error("GL data error:", e);
            // Show server-side message when available (e.g. "Invalid date_from value")
            const serverMsg = e?.data?.message || e?.message || null;
            this.state.error = serverMsg
                ? `Failed to load report: ${serverMsg}`
                : "Failed to load General Ledger data. Please check the console for details.";
        } finally {
            // Only clear loading spinner if this is still the active request
            if (mySeq === this._loadSeq) {
                this.state.loading = false;
            }
        }
    }

    // -------------------------------------------------------------------
    // Lazy line loading
    // -------------------------------------------------------------------

    /**
     * Returns the lazy-load state object for a given key.
     * Creates an empty reactive state if none exists yet.
     * The state object lives inside the useState proxy so OWL tracks
     * mutations to loading/hasMore/lines and re-renders the template.
     */
    _getLinesState(key) {
        if (!this._linesState[key]) {
            this._linesState[key] = {
                lines: [],
                hasMore: false,
                lastId: 0,
                lastDate: null,
                loading: false,
                loaded: false,
            };
        }
        return this._linesState[key];
    }

    /**
     * Load the first page of lines for an account (or one of its partner
     * groups) unless already loaded / loading. Used by every expand path
     * (toggle, expand all, drill-down, reload) in BOTH GL and TB.
     */
    _ensureLines(account, partnerPid = null, journalId = null) {
        if (!account || account.is_unallocated_earnings) return null;
        const key = partnerPid != null
            ? `${account.id}_p${partnerPid}`
            : journalId != null
            ? `${account.id}_j${journalId}`
            : String(account.id);
        const st = this._linesState[key];
        if (st && (st.loading || st.loaded)) return null;
        return this.loadLines(account, partnerPid, journalId);
    }

    /**
     * (Re)load lines for everything currently expanded. Needed after a data
     * reload (which clears all lines but keeps the expanded sets), after
     * drill-down and after "Expand all". Limited concurrency so unfolding
     * hundreds of accounts does not fire hundreds of simultaneous RPCs.
     */
    async _loadExpandedLines() {
        const token = (this._expandSeq = (this._expandSeq || 0) + 1);
        const tasks = [];
        for (const acc of this.state.accounts) {
            if (acc.is_unallocated_earnings || !this.state.expandedAccounts.has(acc.id)) continue;
            if (acc.has_partners && acc.partner_groups && acc.partner_groups.length) {
                for (const pg of acc.partner_groups) {
                    if (this.state.expandedPartners.has(pg.id)) {
                        tasks.push([acc, pg.partner_id]);
                    }
                }
            } else if (acc.has_journals && acc.journal_groups && acc.journal_groups.length) {
                for (const jg of acc.journal_groups) {
                    if (this.state.expandedJournals.has(jg.id)) {
                        tasks.push([acc, null, jg.journal_id]);
                    }
                }
            } else {
                tasks.push([acc, null, null]);
            }
        }
        let next = 0;
        const worker = async () => {
            while (next < tasks.length && token === this._expandSeq) {
                const [acc, pid, jid] = tasks[next++];
                await this._ensureLines(acc, pid, jid);
            }
        };
        await Promise.all([worker(), worker(), worker(), worker()]);
    }

    /**
     * Load the first page of move lines for `account` via /gl_enterprise/get_lines.
     * Resets any previously loaded lines for this account.
     * Called when the user expands an account row (or partner sub-row) in GL mode.
     */
    async loadLines(account, partnerGroupPid, journalGroupJid) {
        const key = partnerGroupPid != null
            ? `${account.id}_p${partnerGroupPid}`
            : journalGroupJid != null
            ? `${account.id}_j${journalGroupJid}`
            : String(account.id);

        // Use _getLinesState to initialize reactive entry if needed
        const st = this._getLinesState(key);
        if (st.loading) return;
        st.loading = true;
        st.lines = [];
        st.hasMore = false;
        st.lastId = 0;
        st.lastDate = null;
        try {
            const params = {
                account_id: account.id,
                date_from: this.state.dateFrom,
                date_to: this.state.dateTo,
                company_id: this.state.companyId,
                target_move: this.state.targetMove,
                journal_ids: this.state.selectedJournalIds.length ? this.state.selectedJournalIds : null,
                account_ids: !this.state.loadAllMode && this.state.selectedAccountIds.length
                    ? this.state.selectedAccountIds : null,
                analytic_ids: this.state.selectedAnalyticIds.length ? this.state.selectedAnalyticIds : null,
            };
            if (partnerGroupPid != null) params.partner_id = partnerGroupPid;
            if (journalGroupJid != null) params.journal_id = journalGroupJid;

            const res = await rpc("/gl_enterprise/get_lines", params);
            if (res) {
                st.lines = res.lines || [];
                st.hasMore = res.has_more || false;
                st.lastId = res.last_id || 0;
                st.lastDate = res.last_date || null;
                st.loaded = true;

                // Patch the account (or partner group) object so the template
                // can render lines via t-foreach="account.move_lines" (or partner.move_lines).
                // account.move_lines is the primary target for plain accounts.
                if (partnerGroupPid != null) {
                    // Patch the matching partner group
                    const pg = (account.partner_groups || []).find(
                        (p) => p.partner_id === partnerGroupPid || p.partner_id === false && partnerGroupPid === 0
                    );
                    if (pg) pg.move_lines = st.lines;
                } else if (journalGroupJid != null) {
                    const jg = (account.journal_groups || []).find((j) => j.journal_id === journalGroupJid);
                    if (jg) jg.move_lines = st.lines;
                } else {
                    account.move_lines = st.lines;
                }
                account._linesKey = key;
            }
        } catch (e) {
            console.error("GL get_lines error:", e);
        } finally {
            st.loading = false;
        }
    }

    /**
     * Load the next page of move lines for `account` (cursor-paginated).
     * Appends to the existing lines.
     */
    async loadMoreLines(account, partnerGroupPid, journalGroupJid) {
        const key = partnerGroupPid != null
            ? `${account.id}_p${partnerGroupPid}`
            : journalGroupJid != null
            ? `${account.id}_j${journalGroupJid}`
            : String(account.id);

        const st = this._linesState[key];
        if (!st || st.loading || !st.hasMore) return;
        st.loading = true;
        try {
            const params = {
                account_id: account.id,
                date_from: this.state.dateFrom,
                date_to: this.state.dateTo,
                company_id: this.state.companyId,
                target_move: this.state.targetMove,
                journal_ids: this.state.selectedJournalIds.length ? this.state.selectedJournalIds : null,
                account_ids: !this.state.loadAllMode && this.state.selectedAccountIds.length
                    ? this.state.selectedAccountIds : null,
                analytic_ids: this.state.selectedAnalyticIds.length ? this.state.selectedAnalyticIds : null,
                last_id: st.lastId,
                last_date: st.lastDate,
            };
            // Running balance of the last line already shown: lets the server
            // skip the whole-history aggregates (O(n) -> O(page)).
            const lastLine = st.lines.length ? st.lines[st.lines.length - 1] : null;
            if (lastLine && lastLine.balance !== undefined && lastLine.balance !== null) {
                params.last_balance = lastLine.balance;
            }
            if (partnerGroupPid != null) params.partner_id = partnerGroupPid;
            if (journalGroupJid != null) params.journal_id = journalGroupJid;

            const res = await rpc("/gl_enterprise/get_lines", params);
            if (res) {
                st.lines = st.lines.concat(res.lines || []);
                st.hasMore = res.has_more || false;
                st.lastId = res.last_id || st.lastId;
                st.lastDate = res.last_date || st.lastDate;

                // Update the account (or partner group) object
                if (partnerGroupPid != null) {
                    const pg = (account.partner_groups || []).find(
                        (p) => p.partner_id === partnerGroupPid || p.partner_id === false && partnerGroupPid === 0
                    );
                    if (pg) pg.move_lines = st.lines;
                } else if (journalGroupJid != null) {
                    const jg = (account.journal_groups || []).find((j) => j.journal_id === journalGroupJid);
                    if (jg) jg.move_lines = st.lines;
                } else {
                    account.move_lines = st.lines;
                }
            }
        } catch (e) {
            console.error("GL loadMoreLines error:", e);
        } finally {
            st.loading = false;
        }
    }

    /**
     * Returns whether lines are currently loading for a given account.
     */
    isLinesLoading(accountId) {
        const st = this._linesState[String(accountId)];
        return st ? st.loading : false;
    }

    /**
     * Returns whether there are more lines to load for a given account.
     */
    hasMoreLines(accountId) {
        const st = this._linesState[String(accountId)];
        return st ? st.hasMore : false;
    }

    // -------------------------------------------------------------------
    // Partner sub-rows: "Load more partners"
    // -------------------------------------------------------------------

    isPartnersLoading(accountId) {
        const st = this._partnerState[String(accountId)];
        return st ? !!st.loading : false;
    }

    async loadMorePartners(account) {
        if (!account || !account.partners_has_more || this.isPartnersLoading(account.id)) {
            return;
        }
        const key = String(account.id);
        this._partnerState[key] = { loading: true };
        const seq = this._loadSeq;
        try {
            const res = await rpc("/gl_enterprise/get_partners", {
                account_id: account.id,
                date_from: this.state.dateFrom,
                date_to: this.state.dateTo,
                company_id: this.state.companyId,
                journal_ids: this.state.selectedJournalIds.length
                    ? this.state.selectedJournalIds : null,
                analytic_ids: this.state.selectedAnalyticIds.length
                    ? this.state.selectedAnalyticIds : null,
                target_move: this.state.targetMove,
                grouped_by: this.state.groupedBy,
                report_type: this.state.reportType,
                offset: account.partner_offset_next || account.partner_groups.length,
                limit: PARTNER_PAGE_SIZE,
            });
            if (seq !== this._loadSeq) {
                return; // filters changed meanwhile: this answer is stale
            }
            const known = new Set(account.partner_groups.map((pg) => pg.id));
            for (const pg of res.partner_groups || []) {
                if (!known.has(pg.id)) {
                    account.partner_groups.push(pg);
                }
            }
            account.partners_has_more = !!res.has_more;
            account.partner_offset_next = res.next_offset;
        } catch (e) {
            console.error("GL get_partners error:", e);
            this.notification.add(
                e?.data?.message || "Could not load more partners. Please try again.",
                { type: "danger" }
            );
        } finally {
            if (this._partnerState[key]) {
                this._partnerState[key].loading = false;
            }
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
        if (type === "month") return getMonthRange(parseIsoDate(this.state.monthRef));
        if (type === "quarter") return getQuarterRange(parseIsoDate(this.state.quarterRef));
        return getFiscalYearRange(parseIsoDate(this.state.fiscalYearRef), this._fyConfig);
    }

    get _fyConfig() {
        return { month: this.state.fyStartMonth, day: this.state.fyStartDay };
    }

    /** "2026" for a calendar fiscal year, "2026-27" when it spans two years. */
    _fiscalYearLabel() {
        const r = getFiscalYearRange(parseIsoDate(this.state.fiscalYearRef), this._fyConfig);
        const fromY = r.from.slice(0, 4);
        const toY = r.to.slice(0, 4);
        return fromY === toY ? fromY : `${fromY}-${toY.slice(2)}`;
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
        let d = parseIsoDate(this.state[refKey]);
        if (type === "fiscal_year") {
            // Keep the exact day: forcing day 1 could move the reference into
            // the previous fiscal year when the FY starts mid-month.
            d = shiftYears(d, delta);
        } else {
            d.setDate(1); // avoid day overflow (e.g. 31 Oct + 1 month = 1 Dec)
            if (type === "month") d.setMonth(d.getMonth() + delta);
            else d.setMonth(d.getMonth() + delta * 3);
        }
        this.state[refKey] = isoDate(d);
        this._applyPeriod(type);
    }

    enableCustomPeriod() {
        this.state.periodMode = "custom";
    }

    get periodPillLabel() {
        if (this.state.periodMode === "month") {
            return longMonthLabel(parseIsoDate(this.state.monthRef));
        }
        if (this.state.periodMode === "quarter") {
            const r = getQuarterRange(parseIsoDate(this.state.quarterRef));
            return quarterLabel(r.from, r.to);
        }
        if (this.state.periodMode === "fiscal_year") {
            return this._fiscalYearLabel();
        }
        return this.dateRangeLabel;
    }

    get currentMonthLabel() {
        return longMonthLabel(parseIsoDate(this.state.monthRef));
    }

    get currentQuarterLabel() {
        const r = getQuarterRange(parseIsoDate(this.state.quarterRef));
        return quarterLabel(r.from, r.to);
    }

    get currentFiscalYearLabel() {
        return this._fiscalYearLabel();
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
        if (this.state.reportType !== type) {
            this.state.reportType = type;
            // Journal grouping only exists in the General Ledger view.
            if (type === "tb") {
                this.state.groupedBy = "none";
                this.state.expandedJournals = new Set();
            }
            this.state.drilldownBreadcrumb = false;
            this._loadData();
        }
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
        this.state.expandedPartners = new Set();
        this.state.expandedJournals = new Set();
        // Lines of the unfolded account are fetched by _doLoadData() once the
        // GL data for the new report type has arrived.
        this._loadData();
    }

    backToTrialBalance(ev) {
        if (ev) ev.preventDefault();
        this.state.reportType = "tb";
        this.state.groupedBy = "none";          // journal grouping is GL-only
        this.state.expandedJournals = new Set();
        this.state.searchQuery = "";
        this.state.drilldownBreadcrumb = false;
        this._loadData();
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
        const dFrom = parseIsoDate(this.state.dateFrom);
        const dTo = parseIsoDate(this.state.dateTo);

        if (this.state.comparisonMode === "previous_period") {
            const diffTime = Math.abs(dTo - dFrom);
            const diffDays =
                (Math.round(diffTime / (1000 * 60 * 60 * 24)) + 1) *
                (this.state.comparisonPeriodCount || 1);
            const compFrom = new Date(dFrom);
            compFrom.setDate(compFrom.getDate() - diffDays);
            const compTo = new Date(dTo);
            compTo.setDate(compTo.getDate() - diffDays);
            return {
                date_from: isoDate(compFrom),
                date_to: isoDate(compTo),
            };
        } else if (this.state.comparisonMode === "same_period_last_year") {
            const compFrom = shiftYears(dFrom, -1);
            const compTo = shiftYears(dTo, -1);
            return {
                date_from: isoDate(compFrom),
                date_to: isoDate(compTo),
            };
        } else if (this.state.comparisonMode === "custom") {
            return {
                date_from: this.state.comparisonDateFrom || this._serverDateFrom || defaultDateFrom(),
                date_to: this.state.comparisonDateTo || this._serverDateTo || defaultDateTo(),
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

    // Analytic accounts dropdown
    openAnalyticDropdown(ev) {
        ev.stopPropagation();
        this.state.analyticDropdownOpen = !this.state.analyticDropdownOpen;
    }

    onAnalyticSearch(ev) {
        this.state.analyticSearch = ev.target.value;
    }

    toggleAnalytic(analyticId) {
        const idx = this.state.selectedAnalyticIds.indexOf(analyticId);
        if (idx === -1) {
            this.state.selectedAnalyticIds.push(analyticId);
        } else {
            this.state.selectedAnalyticIds.splice(idx, 1);
        }
        this._loadData();
    }

    clearAnalytics() {
        this.state.selectedAnalyticIds = [];
        this._loadData();
    }

    // -------------------------------------------------------------------
    // Accounts dropdown — lazy-load filter
    // -------------------------------------------------------------------

    openAccountDropdown(ev) {
        if (ev) ev.stopPropagation();
        this.state.accountDropdownOpen = !this.state.accountDropdownOpen;
    }

    onAccountSearch(ev) {
        this.state.accountSearch = ev.target.value;
    }

    /** Pick/unpick a single account. Picking any account always overrides
     * "Load All" so the view narrows back down to just what's selected. */
    toggleAccountFilter(accountId) {
        const idx = this.state.selectedAccountIds.indexOf(accountId);
        if (idx === -1) {
            this.state.selectedAccountIds.push(accountId);
        } else {
            this.state.selectedAccountIds.splice(idx, 1);
        }
        this.state.loadAllMode = false;
        this._loadData();
    }

    /** Clears the account selection, returning the view to its empty
     * "select accounts" state (unless Load All is separately active). */
    clearAccountFilter() {
        this.state.selectedAccountIds = [];
        this.state.loadAllMode = false;
        this._loadData();
    }

    /** "Load All" — fetches every account, same as the old default
     * behaviour, for whenever the user actually wants the full report. */
    loadAllAccounts(ev) {
        if (ev) ev.stopPropagation();
        this.state.loadAllMode = true;
        this.state.selectedAccountIds = [];
        this.state.accountDropdownOpen = false;
        this._loadData();
    }

    /** Drops back to the empty state (e.g. a "Reset" action) without
     * closing/reopening the client action. */
    resetAccountsView() {
        this.state.loadAllMode = false;
        this.state.selectedAccountIds = [];
        this._loadData();
    }

    /** true while the user hasn't picked any accounts and hasn't asked
     * for "Load All" — used by both _loadData()'s guard and the template
     * to show the "select accounts" prompt instead of a table. */
    get noAccountsSelectedYet() {
        return !this.state.loadAllMode && !this.state.selectedAccountIds.length;
    }

    /** Label for the accounts filter pill */
    get accountFilterPillLabel() {
        if (this.state.loadAllMode) return "All Accounts";
        const sel = this.state.selectedAccountIds;
        if (!sel.length) return "Select Accounts";
        if (sel.length === 1) {
            const a = this.state.allAccounts.find((a) => a.id === sel[0]);
            return a ? `${a.code} ${a.name}` : "1 Account";
        }
        return `${sel.length} Accounts`;
    }

    /** Filtered accounts for the dropdown search box */
    get filteredAccountsForDropdown() {
        const q = (this.state.accountSearch || "").toLowerCase();
        if (!q) return this.state.allAccounts;
        return this.state.allAccounts.filter(
            (a) =>
                (a.name || "").toLowerCase().includes(q) ||
                (a.code || "").toLowerCase().includes(q)
        );
    }

    // -------------------------------------------------------------------
    // Search Handler
    // -------------------------------------------------------------------

    onSearchInput(ev) {
        this.state.searchQuery = ev.target.value;
        this.state.searchSuggestOpen = !!this.state.searchQuery.trim();
    }

    onSearchFocus() {
        if (this.state.searchQuery.trim()) {
            this.state.searchSuggestOpen = true;
        }
    }

    /** Pressing Enter in the top search box resolves the typed text
     * against the full account list (already loaded, cheap) and loads
     * every matching account — this replaces the old behaviour where
     * everything was preloaded and the search box only filtered locally. */
    onSearchKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this._searchAndLoadAccounts();
        } else if (ev.key === "Escape") {
            this.state.searchSuggestOpen = false;
        }
    }

    _searchAndLoadAccounts() {
        const q = (this.state.searchQuery || "").trim().toLowerCase();
        if (!q) return;

        const matches = this.state.allAccounts.filter(
            (a) =>
                (a.code || "").toLowerCase().includes(q) ||
                (a.name || "").toLowerCase().includes(q)
        );

        if (!matches.length) {
            this.notification.add(`No accounts found matching "${this.state.searchQuery}".`, {
                type: "warning",
            });
            return;
        }

        this.state.selectedAccountIds = matches.map((a) => a.id);
        this.state.loadAllMode = false;
        this.state.searchSuggestOpen = false;
        this._loadData();
    }

    /** Up to 20 accounts matching the current search text, for the live
     * autocomplete dropdown under the top search box. */
    get searchSuggestions() {
        const q = (this.state.searchQuery || "").trim().toLowerCase();
        if (!q) return [];
        return this.state.allAccounts
            .filter(
                (a) =>
                    (a.code || "").toLowerCase().includes(q) ||
                    (a.name || "").toLowerCase().includes(q)
            )
            .slice(0, 20);
    }

    /** Clicking a suggestion loads just that one account and clears the
     * search box (the account then shows up as a normal selection in the
     * "Select Accounts" pill). */
    selectSearchSuggestion(account) {
        if (!this.state.selectedAccountIds.includes(account.id)) {
            this.state.selectedAccountIds.push(account.id);
        }
        this.state.loadAllMode = false;
        this.state.searchSuggestOpen = false;
        this.state.searchQuery = "";
        this._loadData();
    }

    clearSearch() {
        this.state.searchQuery = "";
        this.state.searchSuggestOpen = false;
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

    /**
     * Toggle expand/collapse for an account row.
     *
     * BUG FIX (Issue 1): When expanding in GL mode (not TB), we now call
     * loadLines() to fetch the first page of move lines via /get_lines.
     * Previously toggleAccount() only updated the Set and the template
     * iterated account.move_lines which was always [] because get_data was
     * called with include_lines:false but no lazy-load was triggered on expand.
     *
     * In TB mode the account-row expand reveals partner groups (already
     * returned by get_data), not raw move lines, so no loadLines() there.
     */
    toggleAccount(accountId) {
        if (accountId === "unallocated_earnings") return;
        const isExpanding = !this.state.expandedAccounts.has(accountId);
        if (isExpanding) {
            this.state.expandedAccounts.add(accountId);
            // Lazy-load first page of lines in GL *and* TB (TB is fetched with
            // include_lines:false too). Partner-grouped accounts load per
            // partner in togglePartner() instead.
            const account = this.state.accounts.find((a) => a.id === accountId);
            const hasPartnerRows = account && account.has_partners && account.partner_groups && account.partner_groups.length;
            const hasJournalRows = account && account.has_journals && account.journal_groups && account.journal_groups.length;
            if (account && !hasPartnerRows && !hasJournalRows) {
                this._ensureLines(account, null);
            }
        } else {
            this.state.expandedAccounts.delete(accountId);
        }
    }

    /**
     * Toggle expand/collapse for a partner sub-group row (GL and TB).
     * `account` + `partnerGroupPid` are needed to lazy-load that partner's lines.
     */
    togglePartner(partnerKey, account, partnerGroupPid) {
        const isExpanding = !this.state.expandedPartners.has(partnerKey);
        if (isExpanding) {
            this.state.expandedPartners.add(partnerKey);
            if (account && partnerGroupPid != null) {
                this._ensureLines(account, partnerGroupPid);
            }
        } else {
            this.state.expandedPartners.delete(partnerKey);
        }
    }

    /**
     * Toggle expand/collapse for a journal sub-group row (GL, grouped_by=journals).
     * Lines are lazy-loaded per (account, journal) via /get_lines.
     */
    toggleJournalGroup(groupKey, account, journalId) {
        const isExpanding = !this.state.expandedJournals.has(groupKey);
        if (isExpanding) {
            this.state.expandedJournals.add(groupKey);
            if (account && journalId != null) {
                this._ensureLines(account, null, journalId);
            }
        } else {
            this.state.expandedJournals.delete(groupKey);
        }
    }

    isJournalExpanded(groupKey) {
        return this.state.expandedJournals.has(groupKey);
    }

    /** "Group by" option (General Ledger only): 'none' | 'journals'. */
    setGroupedBy(mode) {
        if (this.state.groupedBy !== mode) {
            this.state.groupedBy = mode;
            this.state.expandedJournals = new Set();
            this._loadData();
        }
    }

    expandAll() {
        for (const acc of this.state.accounts) {
            if (acc.is_unallocated_earnings) continue;
            this.state.expandedAccounts.add(acc.id);
            if (acc.has_partners && acc.partner_groups) {
                for (const pg of acc.partner_groups) {
                    this.state.expandedPartners.add(pg.id);
                }
            } else if (acc.has_journals && acc.journal_groups) {
                for (const jg of acc.journal_groups) {
                    this.state.expandedJournals.add(jg.id);
                }
            }
        }
        // Rows are now unfolded: fetch their lines (nothing did before).
        this._loadExpandedLines();
    }

    collapseAll() {
        this.state.expandedAccounts.clear();
        this.state.expandedPartners.clear();
        this.state.expandedJournals.clear();
    }

    isExpanded(accountId) {
        return this.state.expandedAccounts.has(accountId);
    }

    isPartnerExpanded(partnerKey) {
        return this.state.expandedPartners.has(partnerKey);
    }

    // -------------------------------------------------------------------
    // Navigation: close the report and go back to the previous screen
    // -------------------------------------------------------------------

    /** Leaves this client action and returns to whatever the user had open
     * before navigating here (e.g. the Accounting menu). Odoo pushes a
     * history entry for every action, so browser history is the safest
     * way to go back without depending on a specific parent action. */
    closeReport() {
        window.history.back();
    }

    // -------------------------------------------------------------------
    // Theme toggling
    // -------------------------------------------------------------------

    toggleTheme() {
        this.state.lightTheme = !this.state.lightTheme;
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
        const filters = {
            date_from: this.state.dateFrom,
            date_to: this.state.dateTo,
            company_id: this.state.companyId,
            journal_ids: this.state.selectedJournalIds.length
                ? this.state.selectedJournalIds
                : null,
            analytic_ids: this.state.selectedAnalyticIds.length
                ? this.state.selectedAnalyticIds
                : null,
            target_move: this.state.targetMove,
            hide_account_at_0: this.state.hideAccountAt0,
            grouped_by: this.state.groupedBy,
            report_type: this.state.reportType,
            unfold_all: this.anyExpanded,
        };

        // Scope the export to exactly what's on screen:
        // - specific accounts chosen via the Accounts filter / search
        //   (and "Load All" is NOT active) → export only those accounts
        // - otherwise, if the user has typed a search that's narrowing
        //   the currently loaded accounts client-side → export just the
        //   ones currently displayed
        // - "Load All" with no further narrowing → export everything
        //   (account_ids stays unset)
        if (!this.state.loadAllMode && this.state.selectedAccountIds.length) {
            filters.account_ids = this.state.selectedAccountIds;
        } else {
            const q = (this.state.searchQuery || "").trim();
            if (q) {
                // The synthetic "Unallocated Earnings" row has a string id
                // and is not a real account: never send it as an account id.
                const ids = this.displayedAccounts
                    .filter((acc) => !acc.is_unallocated_earnings)
                    .map((acc) => acc.id);
                // An empty list would mean "no filter" (= export EVERYTHING).
                // If the search matches no real account, send an id that
                // cannot exist so the export is empty instead.
                filters.account_ids = ids.length ? ids : [-1];
            }
        }
        return filters;
    }

    _downloadBase64File(base64Content, fileName, mimeType) {
        const link = document.createElement("a");
        link.href = `data:${mimeType};base64,${base64Content}`;
        link.download = fileName;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    /** Message to show for a failed export: server UserError text if any. */
    _exportErrorMessage(e, fallback) {
        const name = e?.data?.name || "";
        // GlExportQueued (server) = "export queued as background job": a
        // UserError subclass whose name does not end with "UserError".
        const isUserError = name.endsWith("UserError") || name.endsWith("GlExportQueued");
        return isUserError && e?.data?.message ? e.data.message : fallback;
    }

    /**
     * Run an export. Default: real binary download through
     * /gl_enterprise/export_file (no base64 / JSON-RPC). The previous JSON
     * flow is kept behind USE_HTTP_DOWNLOAD as an instant rollback.
     */
    async _runExport(format) {
        if (this.noAccountsSelectedYet) {
            this.notification.add(
                _t("Select accounts or click Load All Accounts before exporting."),
                { type: "warning" }
            );
            return;
        }
        const flag = format === "pdf" ? "exportingPdf" : "exportingXlsx";
        if (this.state[flag]) return;
        this.state[flag] = true;
        try {
            if (USE_HTTP_DOWNLOAD) {
                await download({
                    url: "/gl_enterprise/export_file",
                    data: {
                        export_format: format,
                        filters: JSON.stringify(this._exportFilters),
                    },
                });
            } else {
                const result = await rpc("/gl_enterprise/export", {
                    export_format: format,
                    filters: this._exportFilters,
                });
                if (result && result.file_content) {
                    this._downloadBase64File(
                        result.file_content,
                        result.file_name || `report.${format}`,
                        format === "pdf"
                            ? "application/pdf"
                            : "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    );
                } else {
                    await this.action.doAction(result);
                }
            }
        } catch (e) {
            console.error(`${format.toUpperCase()} export error:`, e);
            this.notification.add(
                this._exportErrorMessage(
                    e, `${format.toUpperCase()} export failed. Please try again.`
                ),
                {
                    type: (e?.data?.name || "").endsWith("GlExportQueued") ? "info" : "danger",
                    sticky: true,
                }
            );
        } finally {
            this.state[flag] = false;
        }
    }

    exportPDF() {
        return this._runExport("pdf");
    }

    exportXLSX() {
        return this._runExport("xlsx");
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
    /**
     * Closing balance of an account row: opening balance + period movement.
     * The backend sends it as fin_bal.ending_balance; fall back to computing it
     * so the screen never shows only the period movement as "End Balance".
     */
    accountEndBalance(acc) {
        const fin = (acc && acc.fin_bal) || {};
        if (fin.ending_balance !== undefined && fin.ending_balance !== null) {
            return Number(fin.ending_balance) || 0;
        }
        const init = (acc && acc.init_bal && acc.init_bal.balance) || 0;
        return init + (Number(fin.balance) || 0);
    }

    balanceClass(value) {
        const n = Number(value) || 0;
        if (n > 0.005) return "oca-gl-balance-pos";
        if (n < -0.005) return "oca-gl-balance-neg";
        return "oca-gl-balance-zero";
    }

    /** Label for options dropdown button */
    get optionsDropdownLabel() {
        return this.state.targetMove === "posted"
            ? _t("Posted Entries")
            : _t("Draft & Posted Entries");
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

    /** Label for the Analytic filter pill */
    get analyticPillLabel() {
        const sel = this.state.selectedAnalyticIds;
        if (!sel.length) return "Analytic";
        if (sel.length === 1) {
            const a = this.state.allAnalyticAccounts.find((a) => a.id === sel[0]);
            return a ? a.name : "1 Account";
        }
        return `${sel.length} Analytic Accounts`;
    }

    /** Filtered analytic accounts for dropdown search */
    get filteredAnalyticAccounts() {
        const q = (this.state.analyticSearch || "").toLowerCase();
        if (!q) return this.state.allAnalyticAccounts;
        return this.state.allAnalyticAccounts.filter(
            (a) =>
                (a.name || "").toLowerCase().includes(q) ||
                (a.code || "").toLowerCase().includes(q)
        );
    }

    /** Display date range label */
    get dateRangeLabel() {
        const f = displayDate(this.state.dateFrom);
        const t = displayDate(this.state.dateTo);
        if (!f && !t) return "All Dates";
        return `${f} → ${t}`;
    }

    /** true if any account is expanded.
     * NOTE: single definition on purpose. A second `get anyExpanded` used to
     * exist earlier in this class; the later one always won, so the earlier
     * one was dead code and has been removed. Behaviour is unchanged. */
    get anyExpanded() {
        return this.state.expandedAccounts.size > 0;
    }

    /** Short "from - to" label for the period pill */
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

    /**
     * Grand totals of the rows actually shown. Follows the search box, so the
     * Total row always equals the sum of the visible account rows.
     * (state.grandTotals is still computed on load for any other consumer.)
     */
    get grandTotals() {
        const t = {
            debit: 0, credit: 0, balance: 0, endingBalance: 0, initBalance: 0,
            compDebit: 0, compCredit: 0, compBalance: 0,
        };
        for (const acc of this.displayedAccounts) {
            const fin = acc.fin_bal || {};
            t.debit += Number(fin.debit) || 0;
            t.credit += Number(fin.credit) || 0;
            t.balance += Number(fin.balance) || 0;
            t.initBalance += Number(acc.init_bal && acc.init_bal.balance) || 0;
            t.endingBalance += this.accountEndBalance(acc);
            const comp = acc.comparison_fin_bal;
            if (comp) {
                t.compDebit += Number(comp.debit) || 0;
                t.compCredit += Number(comp.credit) || 0;
                t.compBalance += Number(comp.balance) || 0;
            }
        }
        return t;
    }

    get displayedAccounts() {
        const q = (this.state.searchQuery || "").trim().toLowerCase();
        if (!q) return this.state.accounts;
        return this.state.accounts.filter((acc) => {
            const codeMatch = (acc.code || "").toLowerCase().includes(q);
            const nameMatch = (acc.name || "").toLowerCase().includes(q);
            return codeMatch || nameMatch;
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
    .add("gl_enterprise.GeneralLedgerView", GeneralLedgerView);