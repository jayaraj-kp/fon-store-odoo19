/** @odoo-module **/
/**
 * Partner Ledger — Enterprise Interactive View
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

function displayDate(isoStr) {
    if (!isoStr) return "";
    const [y, m, d] = isoStr.split("-");
    if (!y || !m || !d) return isoStr;
    return `${d}/${m}/${y}`;
}

const ACCOUNT_TYPE_LABELS = {
    receivable: "Customer Ledger",
    non_trade_receivable: "Non Trade Customer Ledger",
    payable: "Supplier Ledger",
    non_trade_payable: "Non Trade Supplier Ledger",
};

const MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
];
const MONTH_ABBR = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

export class PartnerLedgerView extends Component {
    static template = "pl.PartnerLedgerView";
    static props = ["*"];

    setup() {
        this.action = useService("action");
        this.notification = useService("notification");

        const year = new Date().getFullYear();

        this.state = useState({
            lines: [],
            currencyName: "",
            currencySymbol: "",
            companyName: "",
            companyId: null,
            loading: false,
            error: null,
            exportingPdf: false,
            exportingExcel: false,

            dateFrom: `${year}-01-01`,
            dateTo: `${year}-12-31`,
            fiscalYear: year,
            dateMode: "fiscal_year",   // 'month' | 'quarter' | 'fiscal_year' | 'custom'
            periodYear: year,
            periodMonth: new Date().getMonth() + 1,
            periodQuarter: Math.ceil((new Date().getMonth() + 1) / 3),

            targetMove: "posted",
            unfoldAll: false,
            expandOverrides: new Set(),

            showUnpostedWarning: true,
            hasUnposted: false,

            searchTerm: "",
            searchResults: [],
            searchDropdownOpen: false,

            accountTypes: new Set(["receivable", "payable"]),

            selectedPartners: [],
            partnerSearchTerm: "",
            partnerSearchResults: [],

            selectedTags: [],
            tagSearchTerm: "",
            tagSearchResults: [],

            dateDropdownOpen: false,
            accountDropdownOpen: false,
            partnersDropdownOpen: false,
            optionsDropdownOpen: false,
            reportDropdownOpen: false,
            reportView: "partner_ledger", // 'partner_ledger' | 'customer_statement' | 'open_items'
            showFooter: false,
        });

        this.dateDropdownRef = useRef("dateDropdownRef");
        this.accountDropdownRef = useRef("accountDropdownRef");
        this.partnersDropdownRef = useRef("partnersDropdownRef");
        this.optionsDropdownRef = useRef("optionsDropdownRef");
        this.reportDropdownRef = useRef("reportDropdownRef");
        this.searchBoxRef = useRef("searchBoxRef");

        onWillStart(async () => {
            await this._loadInitData();
            await this._applyContextOverrides();
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
        const map = [
            ["dateDropdownOpen", this.dateDropdownRef],
            ["accountDropdownOpen", this.accountDropdownRef],
            ["partnersDropdownOpen", this.partnersDropdownRef],
            ["optionsDropdownOpen", this.optionsDropdownRef],
            ["reportDropdownOpen", this.reportDropdownRef],
            ["searchDropdownOpen", this.searchBoxRef],
        ];
        for (const [key, ref] of map) {
            if (this.state[key]) {
                const el = ref.el;
                if (el && !el.contains(ev.target)) {
                    this.state[key] = false;
                }
            }
        }
    }

    async _loadInitData() {
        try {
            const result = await rpc("/pl/init", {
                company_id: this.state.companyId,
            });
            this.state.companyId = result.company_id;
            this.state.companyName = result.company_name;
            this.state.currencyName = result.currency_name;
            this.state.currencySymbol = result.currency_symbol;
            if (result.date_from) this.state.dateFrom = result.date_from;
            if (result.date_to) this.state.dateTo = result.date_to;
            if (result.fiscal_year) this.state.fiscalYear = result.fiscal_year;
        } catch (e) {
            console.error("Partner Ledger init error:", e);
        }
    }

    async _applyContextOverrides() {
        const ctx = this.props.action && this.props.action.context;
        if (!ctx) return;
        if (ctx.default_report_view) {
            this.state.reportView = ctx.default_report_view;
        }
        if (ctx.default_date_to) {
            this.state.dateTo = ctx.default_date_to;
        }
        if (ctx.default_target_move) {
            this.state.targetMove = ctx.default_target_move;
        }
        if (ctx.default_partner_ids && ctx.default_partner_ids.length) {
            const targetIds = ctx.default_partner_ids.map(Number);
            try {
                const partners = await rpc("/pl/search_partners", {
                    term: "",
                    limit: 100,
                });
                const matched = (partners || []).filter((p) =>
                    targetIds.includes(p.id)
                );
                if (matched.length) {
                    this.state.selectedPartners = matched;
                } else {
                    const results = await Promise.all(
                        targetIds.map((id) =>
                            rpc("/pl/search_partners", { term: String(id), limit: 1 })
                        )
                    );
                    const found = results
                        .flat()
                        .filter((p) => targetIds.includes(p.id));
                    if (found.length) {
                        this.state.selectedPartners = found;
                    }
                }
            } catch (e) {
                console.error("Context partner lookup error:", e);
            }
        }
    }

    async _loadData() {
        this.state.loading = true;
        this.state.error = null;
        try {
            const payload = {
                date_from: this.state.dateFrom,
                date_to: this.state.dateTo,
                company_id: this.state.companyId,
                account_types: Array.from(this.state.accountTypes),
                partner_ids: this.state.selectedPartners.map((p) => p.id),
                tag_ids: this.state.selectedTags.map((t) => t.id),
                target_move: this.state.targetMove,
            };
            const result = await rpc("/pl/get_data", payload);
            this.state.lines = result.lines || [];
            this.state.currencyName = result.currency_name || this.state.currencyName;
            this.state.currencySymbol =
                result.currency_symbol || this.state.currencySymbol;
            this.state.companyName = result.company_name || this.state.companyName;
            this.state.hasUnposted = result.has_unposted || false;
        } catch (e) {
            console.error("Partner Ledger data error:", e);
            this.state.error =
                "Failed to load report data. Please check the console for details.";
        } finally {
            this.state.loading = false;
        }
    }

    // ------------------------------------------------------------------
    // Derived / display helpers
    // ------------------------------------------------------------------
    get dateFilterLabel() {
        switch (this.state.dateMode) {
            case "month":
                return this.monthLabel;
            case "quarter":
                return this.quarterLabel;
            case "custom":
                return `${displayDate(this.state.dateFrom)} – ${displayDate(this.state.dateTo)}`;
            case "fiscal_year":
            default:
                return String(this.state.periodYear);
        }
    }

    get monthLabel() {
        return `${MONTH_NAMES[this.state.periodMonth - 1] || ""} ${this.state.periodYear}`;
    }

    get quarterLabel() {
        const q = this.state.periodQuarter;
        const startMonth = (q - 1) * 3 + 1;
        const endMonth = startMonth + 2;
        return `${MONTH_ABBR[startMonth - 1]} - ${MONTH_ABBR[endMonth - 1]} ${this.state.periodYear}`;
    }

    get accountTypeLabel() {
        const s = this.state.accountTypes;
        const hasR = s.has("receivable");
        const hasP = s.has("payable");
        const hasNR = s.has("non_trade_receivable");
        const hasNP = s.has("non_trade_payable");
        if (hasR && hasP && !hasNR && !hasNP) return "Trade Partners";
        if (hasR && hasP && hasNR && hasNP) return "All Partners";
        if (!s.size) return "Account Type";
        return Array.from(s)
            .map((t) => ACCOUNT_TYPE_LABELS[t])
            .join(", ");
    }

    get partnersFilterLabel() {
        const count = this.state.selectedPartners.length + this.state.selectedTags.length;
        return count ? `Partners (${count})` : "Partners";
    }

    get optionsDropdownLabel() {
        return this.state.targetMove === "posted"
            ? "Posted Entries"
            : "Draft & Posted Entries";
    }

    get filteredLines() {
        // The top search box used to filter these lines client-side by
        // partner name, which left the "Partner Ledger" total row showing
        // the grand total across ALL partners even while searching for
        // one. Search now resolves to real partner selections (exactly
        // like the Partners filter) and reloads from the server, so
        // state.lines already contains exactly — and only — what should
        // be shown, with a correctly scoped total row.
        return this.state.lines;
    }

    isCollapsed(line) {
        if (line.line_type !== "partner") return false;
        const overridden = this.state.expandOverrides.has(line.id);
        return this.state.unfoldAll ? overridden : !overridden;
    }

    isExpandable(line) {
        return line.line_type === "partner" && line.children && line.children.length > 0;
    }

    toggleLine(line) {
        if (!this.isExpandable(line)) return;
        if (this.state.expandOverrides.has(line.id)) {
            this.state.expandOverrides.delete(line.id);
        } else {
            this.state.expandOverrides.add(line.id);
        }
    }

    lineRowClass(line) {
        const classes = ["pl-row"];
        if (this.state.reportView === "customer_statement") classes.push("pl-row-statement");
        if (line.line_type === "total") classes.push("pl-header-band");
        if (line.line_type === "partner") classes.push("pl-partner-row");
        if (line.line_type === "account") classes.push("pl-account-row");
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

    fmtDate(isoStr) {
        return displayDate(isoStr);
    }

    balanceClass(value) {
        return (value || 0) < 0 ? "pl-negative" : "";
    }

    // ------------------------------------------------------------------
    // Dropdown toggles
    // ------------------------------------------------------------------
    openDropdown(name, ev) {
        ev.stopPropagation();
        const key = `${name}DropdownOpen`;
        const wasOpen = this.state[key];
        [
            "dateDropdownOpen",
            "accountDropdownOpen",
            "partnersDropdownOpen",
            "optionsDropdownOpen",
            "reportDropdownOpen",
        ].forEach((k) => (this.state[k] = false));
        this.state[key] = !wasOpen;
    }

    // ------------------------------------------------------------------
    // Date filter — Month / Quarter / Fiscal Year / Custom Dates
    // ------------------------------------------------------------------
    _pad2(n) {
        return String(n).padStart(2, "0");
    }

    _lastDayOfMonth(year, month) {
        // day 0 of the *next* month == last day of `month`
        return new Date(year, month, 0).getDate();
    }

    _monthRange(year, month) {
        const from = `${year}-${this._pad2(month)}-01`;
        const to = `${year}-${this._pad2(month)}-${this._pad2(this._lastDayOfMonth(year, month))}`;
        return { from, to };
    }

    _quarterRange(year, quarter) {
        const startMonth = (quarter - 1) * 3 + 1;
        const endMonth = startMonth + 2;
        const from = `${year}-${this._pad2(startMonth)}-01`;
        const to = `${year}-${this._pad2(endMonth)}-${this._pad2(this._lastDayOfMonth(year, endMonth))}`;
        return { from, to };
    }

    _applyDateRange() {
        let range;
        switch (this.state.dateMode) {
            case "month":
                range = this._monthRange(this.state.periodYear, this.state.periodMonth);
                break;
            case "quarter":
                range = this._quarterRange(this.state.periodYear, this.state.periodQuarter);
                break;
            case "fiscal_year":
                range = { from: `${this.state.periodYear}-01-01`, to: `${this.state.periodYear}-12-31` };
                break;
            default:
                // custom: dateFrom/dateTo are set directly by the date inputs
                return;
        }
        this.state.dateFrom = range.from;
        this.state.dateTo = range.to;
        this.state.fiscalYear = this.state.periodYear;
        this._loadData();
    }

    setDateMode(mode) {
        this.state.dateMode = mode;
        if (mode !== "custom") {
            this._applyDateRange();
        }
    }

    prevMonth(ev) {
        if (ev) ev.stopPropagation();
        this.state.periodMonth -= 1;
        if (this.state.periodMonth < 1) {
            this.state.periodMonth = 12;
            this.state.periodYear -= 1;
        }
        this.state.dateMode = "month";
        this._applyDateRange();
    }

    nextMonth(ev) {
        if (ev) ev.stopPropagation();
        this.state.periodMonth += 1;
        if (this.state.periodMonth > 12) {
            this.state.periodMonth = 1;
            this.state.periodYear += 1;
        }
        this.state.dateMode = "month";
        this._applyDateRange();
    }

    prevQuarter(ev) {
        if (ev) ev.stopPropagation();
        this.state.periodQuarter -= 1;
        if (this.state.periodQuarter < 1) {
            this.state.periodQuarter = 4;
            this.state.periodYear -= 1;
        }
        this.state.dateMode = "quarter";
        this._applyDateRange();
    }

    nextQuarter(ev) {
        if (ev) ev.stopPropagation();
        this.state.periodQuarter += 1;
        if (this.state.periodQuarter > 4) {
            this.state.periodQuarter = 1;
            this.state.periodYear += 1;
        }
        this.state.dateMode = "quarter";
        this._applyDateRange();
    }

    prevFiscalYear(ev) {
        if (ev) ev.stopPropagation();
        this.state.periodYear -= 1;
        this.state.dateMode = "fiscal_year";
        this._applyDateRange();
    }

    nextFiscalYear(ev) {
        if (ev) ev.stopPropagation();
        this.state.periodYear += 1;
        this.state.dateMode = "fiscal_year";
        this._applyDateRange();
    }

    onCustomDateFromChange(ev) {
        this.state.dateFrom = ev.target.value;
        this._loadData();
    }

    onCustomDateToChange(ev) {
        this.state.dateTo = ev.target.value;
        this._loadData();
    }

    // ------------------------------------------------------------------
    // Account type filter
    // ------------------------------------------------------------------
    toggleAccountType(type) {
        if (this.state.accountTypes.has(type)) {
            this.state.accountTypes.delete(type);
        } else {
            this.state.accountTypes.add(type);
        }
        this._loadData();
    }

    isAccountTypeChecked(type) {
        return this.state.accountTypes.has(type);
    }

    // ------------------------------------------------------------------
    // Partners / Tags filter
    // ------------------------------------------------------------------
    async onPartnerSearchInput(ev) {
        this.state.partnerSearchTerm = ev.target.value;
        try {
            const results = await rpc("/pl/search_partners", {
                term: this.state.partnerSearchTerm,
            });
            this.state.partnerSearchResults = results || [];
        } catch (e) {
            console.error("Partner search error:", e);
        }
    }

    async onTagSearchInput(ev) {
        this.state.tagSearchTerm = ev.target.value;
        try {
            const results = await rpc("/pl/search_tags", {
                term: this.state.tagSearchTerm,
            });
            this.state.tagSearchResults = results || [];
        } catch (e) {
            console.error("Tag search error:", e);
        }
    }

    addPartner(partner) {
        if (!this.state.selectedPartners.find((p) => p.id === partner.id)) {
            this.state.selectedPartners.push(partner);
            this._loadData();
        }
    }

    removePartner(partnerId) {
        this.state.selectedPartners = this.state.selectedPartners.filter(
            (p) => p.id !== partnerId
        );
        this._loadData();
    }

    addTag(tag) {
        if (!this.state.selectedTags.find((t) => t.id === tag.id)) {
            this.state.selectedTags.push(tag);
            this._loadData();
        }
    }

    removeTag(tagId) {
        this.state.selectedTags = this.state.selectedTags.filter(
            (t) => t.id !== tagId
        );
        this._loadData();
    }

    // ------------------------------------------------------------------
    // Posted / draft + unfold all
    // ------------------------------------------------------------------
    setTargetMove(mode, ev) {
        if (ev) ev.stopPropagation();
        if (this.state.targetMove !== mode) {
            this.state.targetMove = mode;
            this._loadData();
        }
    }

    toggleDraftEntries(ev) {
        if (ev) ev.stopPropagation();
        this.state.targetMove = this.state.targetMove === "all" ? "posted" : "all";
        this._loadData();
    }

    toggleUnfoldAll(ev) {
        if (ev) ev.stopPropagation();
        this.state.unfoldAll = !this.state.unfoldAll;
        this.state.expandOverrides = new Set();
    }

    toggleShowFooter(ev) {
        if (ev) ev.stopPropagation();
        this.state.showFooter = !this.state.showFooter;
    }

    // ------------------------------------------------------------------
    // Report switcher (Partner Ledger + Statement of Account implemented;
    // Open Items is a placeholder)
    // ------------------------------------------------------------------
    get reportTitleLabel() {
        const types = this.state.accountTypes;
        if (types.size === 0) return "Partner Ledger";
        const hasReceivable = types.has("receivable") || types.has("non_trade_receivable");
        const hasPayable = types.has("payable") || types.has("non_trade_payable");
        if (hasReceivable && !hasPayable) return "Customer Ledger";
        if (hasPayable && !hasReceivable) return "Supplier Ledger";
        return "Ledger";
    }

    get reportViewLabel() {
        if (this.state.reportView === "customer_statement") return "Statement of Account";
        if (this.state.reportView === "open_items") return "Open Items";
        return this.reportTitleLabel;
    }

    selectReportView(view, ev) {
        if (ev) ev.stopPropagation();
        this.state.reportDropdownOpen = false;
        if (view === "open_items") {
            this.notification.add(
                "This report view isn't available yet in this module.",
                { type: "info" }
            );
            return;
        }
        this.state.reportView = view;
    }

    // ------------------------------------------------------------------
    // Search box — resolves typed text to real partners and loads them,
    // the same way picking a partner from the Partners filter does. This
    // is what keeps the "Partner Ledger" total row scoped correctly to
    // whatever is currently selected instead of always showing the
    // grand total across every partner.
    // ------------------------------------------------------------------
    onSearchInput(ev) {
        this.state.searchTerm = ev.target.value;
        const term = this.state.searchTerm.trim();
        clearTimeout(this._searchDebounce);
        if (!term) {
            this.state.searchResults = [];
            this.state.searchDropdownOpen = false;
            return;
        }
        this.state.searchDropdownOpen = true;
        this._searchDebounce = setTimeout(() => this._runPartnerSearch(term), 250);
    }

    onSearchFocus() {
        if (this.state.searchTerm.trim() && this.state.searchResults.length) {
            this.state.searchDropdownOpen = true;
        }
    }

    onSearchKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this._searchAndSelectPartners();
        } else if (ev.key === "Escape") {
            this.state.searchDropdownOpen = false;
        }
    }

    async _runPartnerSearch(term) {
        try {
            const results = await rpc("/pl/search_partners", { term });
            this.state.searchResults = results || [];
        } catch (e) {
            console.error("Partner search error:", e);
        }
    }

    /** Pressing Enter adds every currently-suggested partner (usually
     * just one) to the selection and loads them, mirroring how choosing
     * a result from the Partners dropdown behaves. */
    async _searchAndSelectPartners() {
        const term = this.state.searchTerm.trim();
        if (!term) return;

        let results = this.state.searchResults;
        if (!results.length) {
            try {
                results = (await rpc("/pl/search_partners", { term })) || [];
            } catch (e) {
                console.error("Partner search error:", e);
                results = [];
            }
        }

        if (!results.length) {
            this.notification.add(`No partners found matching "${term}".`, {
                type: "warning",
            });
            return;
        }

        for (const p of results) {
            if (!this.state.selectedPartners.find((sp) => sp.id === p.id)) {
                this.state.selectedPartners.push(p);
            }
        }
        this._clearSearchBox();
        this._loadData();
    }

    /** Clicking a suggestion selects just that one partner. */
    selectSearchResult(partner) {
        this.addPartner(partner);
        this._clearSearchBox();
    }

    _clearSearchBox() {
        this.state.searchTerm = "";
        this.state.searchResults = [];
        this.state.searchDropdownOpen = false;
    }

    clearSearch() {
        this._clearSearchBox();
    }

    dismissWarning() {
        this.state.showUnpostedWarning = false;
    }

    openPartner(partnerId) {
        if (!partnerId) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            res_id: partnerId,
            views: [[false, "form"]],
            target: "current",
        });
    }

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

    openPartnerJournalItems(line, ev) {
        if (ev) ev.stopPropagation();
        if (!line.partner_id) return;
        const domain = [
            ["partner_id", "=", line.partner_id],
            ["date", ">=", this.state.dateFrom],
            ["date", "<=", this.state.dateTo],
            ["display_type", "not in", ["line_section", "line_note"]],
        ];
        if (this.state.targetMove === "posted") {
            domain.push(["parent_state", "=", "posted"]);
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Journal Items",
            res_model: "account.move.line",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain,
            target: "current",
        });
    }

    async exportPDF() {
        if (this.state.exportingPdf) return;
        this.state.exportingPdf = true;
        try {
            const result = await rpc("/pl/export_pdf", {
                date_from: this.state.dateFrom,
                date_to: this.state.dateTo,
                company_id: this.state.companyId,
                account_types: Array.from(this.state.accountTypes),
                partner_ids: this.state.selectedPartners.map((p) => p.id),
                tag_ids: this.state.selectedTags.map((t) => t.id),
                target_move: this.state.targetMove,
                report_view: this.state.reportView,
                show_footer: this.state.showFooter,
            });
            if (result?.file_content) {
                const link = document.createElement("a");
                link.href = "data:application/pdf;base64," + result.file_content;
                link.download = result.file_name || "partner_ledger.pdf";
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
        if (this.state.exportingExcel) return;
        this.state.exportingExcel = true;
        try {
            const result = await rpc("/pl/export_excel", {
                date_from: this.state.dateFrom,
                date_to: this.state.dateTo,
                company_id: this.state.companyId,
                account_types: Array.from(this.state.accountTypes),
                partner_ids: this.state.selectedPartners.map((p) => p.id),
                tag_ids: this.state.selectedTags.map((t) => t.id),
                target_move: this.state.targetMove,
                report_view: this.state.reportView,
            });
            if (result?.file_content) {
                const link = document.createElement("a");
                link.href = "data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64," + result.file_content;
                link.download = result.file_name || "partner_ledger.xlsx";
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
            this.state.exportingExcel = false;
        }
    }

    closeReport() {
        window.history.back();
    }
}

registry.category("actions").add("pl.PartnerLedgerView", PartnerLedgerView);