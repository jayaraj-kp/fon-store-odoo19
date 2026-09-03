/** @odoo-module **/
/**
 * Aged Receivable Report — Enterprise Interactive View
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

const MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
];
const MONTH_ABBR = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

function endOfMonth(year, month) {
    return new Date(year, month, 0).getDate();
}

function formatMonthYear(year, month) {
    return `${MONTH_NAMES[month - 1]} ${year}`;
}

function formatQuarter(year, quarter) {
    const start = (quarter - 1) * 3 + 1;
    const end = start + 2;
    return `${MONTH_ABBR[start - 1]} ${year} - ${MONTH_ABBR[end - 1]} ${year}`;
}

export class AgedReceivableView extends Component {
    static template = "pl.AgedReceivableView";
    static props = ["*"];

    setup() {
        this.action = useService("action");
        this.notification = useService("notification");

        const today = new Date();
        const todayStr = today.toISOString().split("T")[0];
        const currentMonth = today.getMonth() + 1;
        const currentYear = today.getFullYear();
        const currentQuarter = Math.ceil(currentMonth / 3);

        this.state = useState({
            lines: [],
            bucketLabels: [],
            currencyName: "",
            currencySymbol: "",
            companyName: "",
            companyId: null,
            loading: false,
            error: null,
            exportingPdf: false,
            exportingExcel: false,

            dateAsOf: todayStr,
            dateMode: "today",

            targetMove: "posted",
            unfoldAll: false,
            expandOverrides: new Set(),

            showUnpostedWarning: true,
            hasUnposted: false,

            accountTypes: new Set(["receivable"]),
            basedOn: "due_date",
            daysInterval: 30,
            customDaysInput: "30",

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
            intervalDropdownOpen: false,
            basedOnDropdownOpen: false,
            searchDropdownOpen: false,

            searchTerm: "",
            searchResults: [],

            periodMonth: currentMonth,
            periodYear: currentYear,
            periodQuarter: currentQuarter,
        });

        this.dateDropdownRef = useRef("dateDropdownRef");
        this.accountDropdownRef = useRef("accountDropdownRef");
        this.partnersDropdownRef = useRef("partnersDropdownRef");
        this.optionsDropdownRef = useRef("optionsDropdownRef");
        this.intervalDropdownRef = useRef("intervalDropdownRef");
        this.basedOnDropdownRef = useRef("basedOnDropdownRef");
        this.searchBoxRef = useRef("searchBoxRef");

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
        const map = [
            ["dateDropdownOpen", this.dateDropdownRef],
            ["accountDropdownOpen", this.accountDropdownRef],
            ["partnersDropdownOpen", this.partnersDropdownRef],
            ["optionsDropdownOpen", this.optionsDropdownRef],
            ["intervalDropdownOpen", this.intervalDropdownRef],
            ["basedOnDropdownOpen", this.basedOnDropdownRef],
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
            const result = await rpc("/pl/aged/init", {
                company_id: this.state.companyId,
            });
            this.state.companyId = result.company_id;
            this.state.companyName = result.company_name;
            this.state.currencyName = result.currency_name;
            this.state.currencySymbol = result.currency_symbol;
            if (result.date_as_of) this.state.dateAsOf = result.date_as_of;
        } catch (e) {
            console.error("Aged Receivable init error:", e);
        }
    }

    async _loadData() {
        this.state.loading = true;
        this.state.error = null;
        try {
            const payload = {
                date_as_of: this.state.dateAsOf,
                company_id: this.state.companyId,
                account_types: Array.from(this.state.accountTypes),
                partner_ids: this.state.selectedPartners.map((p) => p.id),
                tag_ids: this.state.selectedTags.map((t) => t.id),
                target_move: this.state.targetMove,
                days_interval: this.state.daysInterval,
                based_on: this.state.basedOn,
            };
            const result = await rpc("/pl/aged/get_data", payload);
            this.state.lines = result.lines || [];
            this.state.bucketLabels = result.bucket_labels || [];
            this.state.currencyName = result.currency_name || this.state.currencyName;
            this.state.currencySymbol =
                result.currency_symbol || this.state.currencySymbol;
            this.state.companyName = result.company_name || this.state.companyName;
            this.state.hasUnposted = result.has_unposted || false;
        } catch (e) {
            console.error("Aged Receivable data error:", e);
            this.state.error =
                "Failed to load report data. Please check the console for details.";
        } finally {
            this.state.loading = false;
        }
    }

    // ------------------------------------------------------------------
    // Date filter labels
    // ------------------------------------------------------------------
    get dateFilterLabel() {
        return displayDate(this.state.dateAsOf);
    }

    get dateModeLabel() {
        switch (this.state.dateMode) {
            case "today":
                return "Today";
            case "end_of_month":
                return `End of ${formatMonthYear(this.state.periodYear, this.state.periodMonth)}`;
            case "end_of_quarter":
                return `End of ${formatQuarter(this.state.periodYear, this.state.periodQuarter)}`;
            case "end_of_fiscal_year":
                return `End of Fiscal Year ${this.state.periodYear}`;
            case "specific":
                return displayDate(this.state.dateAsOf);
            default:
                return displayDate(this.state.dateAsOf);
        }
    }

    get endOfMonthLabel() {
        const d = endOfMonth(this.state.periodYear, this.state.periodMonth);
        return `${d} ${formatMonthYear(this.state.periodYear, this.state.periodMonth)}`;
    }

    get endOfQuarterLabel() {
        return formatQuarter(this.state.periodYear, this.state.periodQuarter);
    }

    get fiscalYearLabel() {
        return String(this.state.periodYear);
    }

    get accountTypeLabel() {
        const s = this.state.accountTypes;
        const hasR = s.has("receivable");
        const hasP = s.has("payable");
        if (hasR && !hasP) return "Receivable";
        if (!hasR && hasP) return "Payable";
        if (hasR && hasP) return "Receivable & Payable";
        return "Account Type";
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

    get intervalLabel() {
        return `${this.state.daysInterval} Days`;
    }

    get basedOnLabel() {
        return this.state.basedOn === "due_date" ? "Based on Due Date" : "Based on Invoice Date";
    }

    get filteredLines() {
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

    bucketValue(line, bucketIdx) {
        if (line.line_type === "account") {
            if (line.bucket === String(bucketIdx)) {
                return line.balance || 0;
            }
            return 0;
        }
        if (line.buckets) {
            return line.buckets[String(bucketIdx)] || 0;
        }
        return 0;
    }

    // ------------------------------------------------------------------
    // Dropdown toggles
    // ------------------------------------------------------------------
    openDropdown(name, ev) {
        if (ev) ev.stopPropagation();
        const key = `${name}DropdownOpen`;
        const wasOpen = this.state[key];
        [
            "dateDropdownOpen",
            "accountDropdownOpen",
            "partnersDropdownOpen",
            "optionsDropdownOpen",
            "intervalDropdownOpen",
            "basedOnDropdownOpen",
        ].forEach((k) => (this.state[k] = false));
        this.state[key] = !wasOpen;
    }

    // ------------------------------------------------------------------
    // Date filter — enterprise style
    // ------------------------------------------------------------------
    setToday() {
        this.state.dateAsOf = new Date().toISOString().split("T")[0];
        this.state.dateMode = "today";
        this.state.dateDropdownOpen = false;
        this._loadData();
    }

    setEndOfMonth() {
        const d = endOfMonth(this.state.periodYear, this.state.periodMonth);
        const mm = String(this.state.periodMonth).padStart(2, "0");
        this.state.dateAsOf = `${this.state.periodYear}-${mm}-${String(d).padStart(2, "0")}`;
        this.state.dateMode = "end_of_month";
        this.state.dateDropdownOpen = false;
        this._loadData();
    }

    setEndOfQuarter() {
        const q = this.state.periodQuarter;
        const endMonth = q * 3;
        const d = endOfMonth(this.state.periodYear, endMonth);
        const mm = String(endMonth).padStart(2, "0");
        this.state.dateAsOf = `${this.state.periodYear}-${mm}-${String(d).padStart(2, "0")}`;
        this.state.dateMode = "end_of_quarter";
        this.state.dateDropdownOpen = false;
        this._loadData();
    }

    setEndOfFiscalYear() {
        this.state.dateAsOf = `${this.state.periodYear}-12-31`;
        this.state.dateMode = "end_of_fiscal_year";
        this.state.dateDropdownOpen = false;
        this._loadData();
    }

    setSpecificDate() {
        this.state.dateMode = "specific";
    }

    onSpecificDateChange(ev) {
        this.state.dateAsOf = ev.target.value;
        this.state.dateDropdownOpen = false;
        this._loadData();
    }

    prevMonth(ev) {
        if (ev) ev.stopPropagation();
        this.state.periodMonth -= 1;
        if (this.state.periodMonth < 1) {
            this.state.periodMonth = 12;
            this.state.periodYear -= 1;
        }
    }

    nextMonth(ev) {
        if (ev) ev.stopPropagation();
        this.state.periodMonth += 1;
        if (this.state.periodMonth > 12) {
            this.state.periodMonth = 1;
            this.state.periodYear += 1;
        }
    }

    prevQuarter(ev) {
        if (ev) ev.stopPropagation();
        this.state.periodQuarter -= 1;
        if (this.state.periodQuarter < 1) {
            this.state.periodQuarter = 4;
            this.state.periodYear -= 1;
        }
    }

    nextQuarter(ev) {
        if (ev) ev.stopPropagation();
        this.state.periodQuarter += 1;
        if (this.state.periodQuarter > 4) {
            this.state.periodQuarter = 1;
            this.state.periodYear += 1;
        }
    }

    prevFiscalYear(ev) {
        if (ev) ev.stopPropagation();
        this.state.periodYear -= 1;
    }

    nextFiscalYear(ev) {
        if (ev) ev.stopPropagation();
        this.state.periodYear += 1;
    }

    // ------------------------------------------------------------------
    // Based on filter
    // ------------------------------------------------------------------
    setBasedOn(mode) {
        this.state.basedOn = mode;
        this.state.basedOnDropdownOpen = false;
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
    // Days interval
    // ------------------------------------------------------------------
    setDaysInterval(interval) {
        this.state.daysInterval = interval;
        this.state.customDaysInput = String(interval);
        this.state.intervalDropdownOpen = false;
        this._loadData();
    }

    onCustomDaysChange(ev) {
        this.state.customDaysInput = ev.target.value;
    }

    onCustomDaysKeydown(ev) {
        if (ev.key === "Enter") {
            const val = parseInt(this.state.customDaysInput, 10);
            if (val && val > 0) {
                this.state.daysInterval = val;
                this.state.intervalDropdownOpen = false;
                this._loadData();
            }
        }
    }

    applyCustomDays() {
        const val = parseInt(this.state.customDaysInput, 10);
        if (val && val > 0) {
            this.state.daysInterval = val;
            this.state.intervalDropdownOpen = false;
            this._loadData();
        }
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

    // ------------------------------------------------------------------
    // Search
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
            ["date", "<=", this.state.dateAsOf],
            ["display_type", "not in", ["line_section", "line_note"]],
        ];
        if (this.state.targetMove === "posted") {
            domain.push(["parent_state", "=", "posted"]);
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Amounts to Settle",
            res_model: "account.move.line",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain,
            target: "current",
        });
    }

    openCustomerStatement(line, ev) {
        if (ev) ev.stopPropagation();
        if (!line.partner_id) return;
        this.action.doAction({
            type: "ir.actions.client",
            tag: "pl.PartnerLedgerView",
            name: "Statement of Account",
            target: "current",
            context: {
                default_partner_ids: [line.partner_id],
                default_report_view: "customer_statement",
                default_date_to: this.state.dateAsOf,
                default_target_move: this.state.targetMove,
            },
        });
    }

    openAmountDetails(line, bucketIdx, ev) {
        if (ev) ev.stopPropagation();
        if (!line.partner_id && !line.move_id) return;
        const domain = [
            ["display_type", "not in", ["line_section", "line_note"]],
            ["date", "<=", this.state.dateAsOf],
        ];
        if (line.partner_id) {
            domain.push(["partner_id", "=", line.partner_id]);
        }
        if (line.move_id) {
            domain.push(["move_id", "=", line.move_id]);
        }
        if (this.state.targetMove === "posted") {
            domain.push(["parent_state", "=", "posted"]);
        }
        if (this.state.accountTypes.has("receivable")) {
            domain.push(["account_type", "=", "asset_receivable"]);
        }
        if (this.state.accountTypes.has("payable")) {
            domain.push(["account_type", "=", "liability_payable"]);
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
            const result = await rpc("/pl/aged/export_pdf", {
                date_as_of: this.state.dateAsOf,
                company_id: this.state.companyId,
                account_types: Array.from(this.state.accountTypes),
                partner_ids: this.state.selectedPartners.map((p) => p.id),
                tag_ids: this.state.selectedTags.map((t) => t.id),
                target_move: this.state.targetMove,
                days_interval: this.state.daysInterval,
                based_on: this.state.basedOn,
            });
            if (result?.file_content) {
                const link = document.createElement("a");
                link.href = "data:application/pdf;base64," + result.file_content;
                link.download = result.file_name || "aged_receivable.pdf";
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
            const result = await rpc("/pl/aged/export_excel", {
                date_as_of: this.state.dateAsOf,
                company_id: this.state.companyId,
                account_types: Array.from(this.state.accountTypes),
                partner_ids: this.state.selectedPartners.map((p) => p.id),
                tag_ids: this.state.selectedTags.map((t) => t.id),
                target_move: this.state.targetMove,
                days_interval: this.state.daysInterval,
                based_on: this.state.basedOn,
            });
            if (result?.file_content) {
                const link = document.createElement("a");
                link.href = "data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64," + result.file_content;
                link.download = result.file_name || "aged_receivable.xlsx";
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

registry.category("actions").add("pl.AgedReceivableView", AgedReceivableView);
