/** @odoo-module **/

import { Component, useState, onWillStart, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

// The partner headers are always loaded; the documents of a partner are loaded
// from the server only when that partner is opened.
const AUTO_EXPAND_MAX_PARTNERS = 20;  // small reports open everything, like before
const MAX_EXPAND_ALL = 100;           // "Expand all" opens at most this many partners
const LINES_CHUNK = 100;              // partners per lines request (server cap: 200)
const SEARCH_DEBOUNCE_MS = 450;

export class DueReportView extends Component {
    static template = "custom_due_reports.DueReportView";
    static props = ["*"];

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.notification = useService("notification");

        const today = new Date();
        const yyyy = today.getFullYear();
        const mm = String(today.getMonth() + 1).padStart(2, "0");
        const dd = String(today.getDate()).padStart(2, "0");
        const todayStr = `${yyyy}-${mm}-${dd}`;
        const firstDayOfYear = `${yyyy}-01-01`;

        const params = this.props.action?.params || {};
        const context = this.props.action?.context || {};

        this.state = useState({
            move_type: params.move_type || context.default_move_type || "out_invoice",
            date_from: params.date_from !== undefined && params.date_from !== false ? params.date_from : "",
            date_to: params.date_to !== undefined && params.date_to !== false ? params.date_to : todayStr,
            partner_ids: params.partner_ids ? [...params.partner_ids] : [],
            analytic_account_ids: params.analytic_account_ids ? [...params.analytic_account_ids] : [],
            only_due: params.only_due !== undefined ? params.only_due : true,
            due_filter: params.due_filter || "all",
            show_grand_total: params.show_grand_total !== undefined ? params.show_grand_total : true,
            show_address: params.show_address !== undefined ? params.show_address : false,
            company_id: params.company_id || false,
            theme: localStorage.getItem("due_report_theme") || "light",
            searchQuery: "",
            partnerSearch: "",
            isPartnerDropdownOpen: false,
            analyticSearch: "",
            isAnalyticDropdownOpen: false,
            expandedGroupIds: [],
            loadingGroupIds: [],
            linesVersion: 0,
            loading: true,
            // Pagination state
            currentPage: 1,
            pageSize: 20,
            data: {
                groups: [],
                totals: {},
                currency: { symbol: "$", position: "after" },
                currencies: [],
                company: {},
                partners_list: [],
                analytics_list: [],
                report_title: "Customer Due Report",
            },
            // --- Currency filter state ---
            currencies: [],
            selectedCurrencyId: null,
            selectedCurrencyName: "",
            selectedCurrencySymbol: "",
            customRates: {},
            customRateInverted: {},
            conversionApplied: false,
            useTransactionRates: true,
            isCurrencyDropdownOpen: false,
        });

        this._reqSeq = 0;
        this._listsLoaded = false;
        this._searchTimer = null;
        onWillUnmount(() => clearTimeout(this._searchTimer));

        onWillStart(async () => {
            await this.loadReportData();
        });
    }

    toggleTheme() {
        this.state.theme = this.state.theme === "dark" ? "light" : "dark";
        try {
            localStorage.setItem("due_report_theme", this.state.theme);
        } catch (e) {
            console.warn("Could not save theme preference", e);
        }
    }

    /** Options shared by the report data call and the per-partner lines call. */
    _reportOptions() {
        return {
            move_type: this.state.move_type,
            date_from: this.state.date_from,
            date_to: this.state.date_to,
            partner_ids: this.state.partner_ids,
            analytic_account_ids: this.state.analytic_account_ids,
            only_due: this.state.only_due,
            due_filter: this.state.due_filter,
            show_grand_total: this.state.show_grand_total,
            show_address: this.state.show_address,
            company_id: this.state.company_id,
            // false -> every partner in its own transaction currency;
            // otherwise the server converts everything to the chosen one.
            currency_opts: this._getCurrencyOptsPayload(),
            // The search text is applied on the server, so the partner
            // headers, the KPI cards and the lines always agree.
            search_query: (this.state.searchQuery || "").trim(),
        };
    }

    async loadReportData() {
        // A newer request makes every older answer obsolete (fast typing,
        // quick filter changes).
        const seq = ++this._reqSeq;
        this.state.loading = true;
        this.state.currentPage = 1;
        try {
            const options = {
                ...this._reportOptions(),
                // Partner headers only; lines come when a partner is expanded.
                lazy_lines: true,
                // Selector lists / logo are static: ask for them once.
                include_lists: !this._listsLoaded,
            };
            const result = await this.orm.call(
                "due.report.wizard",
                "get_due_report_data",
                [],
                { options }
            );
            if (seq !== this._reqSeq) {
                return;
            }
            if (result) {
                const prev = this.state.data || {};
                this.state.data = {
                    ...result,
                    partners_list: result.partners_list ?? prev.partners_list ?? [],
                    analytics_list: result.analytics_list ?? prev.analytics_list ?? [],
                    currencies: result.currencies ?? prev.currencies ?? [],
                    company: {
                        ...(result.company || {}),
                        logo: (result.company && result.company.logo)
                            || (prev.company && prev.company.logo) || false,
                    },
                };
                this.state.currencies = this.state.data.currencies;
                this._listsLoaded = true;
                this.state.expandedGroupIds = [];
                this.state.loadingGroupIds = [];
                this.state.linesVersion += 1;
            }
        } catch (error) {
            if (seq !== this._reqSeq) {
                return;
            }
            console.error("Failed to load due report data", error);
            this.notification.add("Failed to load report data: " + this._errorMessage(error), {
                type: "danger",
            });
        } finally {
            if (seq === this._reqSeq) {
                this.state.loading = false;
            }
        }
        if (seq === this._reqSeq) {
            // Small reports keep the old behaviour (everything open); big ones
            // start collapsed and load a partner's lines on demand.
            const groups = this.state.data.groups || [];
            if (groups.length > 0 && groups.length <= AUTO_EXPAND_MAX_PARTNERS) {
                await this._expandGroups(groups.map((g) => g.partner_id));
            }
        }
    }

    // --- Lazy lines (server side pagination of the documents) ---
    async _expandGroups(partnerIds) {
        const expanded = new Set(this.state.expandedGroupIds);
        for (const id of partnerIds) {
            expanded.add(id);
        }
        this.state.expandedGroupIds = [...expanded];
        await this._loadLinesFor(partnerIds);
    }

    /** Fetch (in chunks) the lines of the partners that do not have them yet. */
    async _loadLinesFor(partnerIds) {
        const groups = this.state.data.groups || [];
        const ids = partnerIds.filter((id) => {
            const group = groups.find((g) => g.partner_id === id);
            return group && !group.lines_loaded && !this.state.loadingGroupIds.includes(id);
        });
        if (!ids.length) {
            return;
        }
        const seq = this._reqSeq;
        this.state.loadingGroupIds.push(...ids);
        try {
            for (let i = 0; i < ids.length; i += LINES_CHUNK) {
                const chunk = ids.slice(i, i + LINES_CHUNK);
                const result = await this.orm.call(
                    "due.report.wizard",
                    "get_due_report_partner_lines",
                    [],
                    { options: this._reportOptions(), partner_ids: chunk }
                );
                if (seq !== this._reqSeq) {
                    return; // the report was reloaded meanwhile
                }
                for (const group of this.state.data.groups) {
                    const loaded = result && result[group.partner_id];
                    if (loaded && chunk.includes(group.partner_id)) {
                        group.lines = loaded.lines;
                        group.lines_loaded = true;
                    }
                }
                this.state.linesVersion += 1;
            }
        } catch (error) {
            if (seq !== this._reqSeq) {
                return;
            }
            console.error("Failed to load due report lines", error);
            this.notification.add("Failed to load documents: " + this._errorMessage(error), {
                type: "danger",
            });
            // Close the partners whose lines could not be loaded.
            this.state.expandedGroupIds = this.state.expandedGroupIds.filter(
                (id) => !ids.includes(id) || (this.state.data.groups.find((g) => g.partner_id === id) || {}).lines_loaded
            );
        } finally {
            if (seq === this._reqSeq) {
                this.state.loadingGroupIds = this.state.loadingGroupIds.filter((id) => !ids.includes(id));
            }
        }
    }

    // --- Search (applied on the server, debounced) ---
    onSearchInput(ev) {
        this.state.searchQuery = ev.target.value;
        clearTimeout(this._searchTimer);
        this._searchTimer = setTimeout(() => this.loadReportData(), SEARCH_DEBOUNCE_MS);
    }

    onSearchClear() {
        clearTimeout(this._searchTimer);
        this.state.searchQuery = "";
        this.loadReportData();
    }

    async onFilterChange() {
        await this.loadReportData();
    }

    async setMoveType(type) {
        if (this.state.move_type !== type) {
            this.state.move_type = type;
            this.state.partner_ids = [];
            this.state.searchQuery = "";
            await this.loadReportData();
        }
    }

    setDueFilter(filter) {
        this.state.due_filter = filter;
        this.state.currentPage = 1;
    }

    // --- Currency filter payload for server-side (PDF/XLSX) conversion ---
    _getCurrencyOptsPayload() {
        if (!this.state.conversionApplied || !this.state.selectedCurrencyId) {
            return false;
        }
        return {
            currency_id: this.state.selectedCurrencyId,
            symbol: this.state.selectedCurrencySymbol,
            name: this.state.selectedCurrencyName,
            use_transaction_rates: this.state.useTransactionRates,
            // Custom mode: 1 <transaction currency> = <rate> <selected currency>
            rates: this._getCustomRatesPayload(),
        };
    }

    _getCustomRatesPayload() {
        // Server wants: 1 <transaction currency> = rate <selected currency>.
        // A swapped row is typed as 1 <selected> = x <transaction>, so invert it.
        const rates = {};
        for (const [currencyId, value] of Object.entries(this.state.customRates)) {
            const typed = parseFloat(value);
            if (typed > 0) {
                rates[currencyId] = this.state.customRateInverted[currencyId] ? 1 / typed : typed;
            }
        }
        return rates;
    }

    // Odoo puts the readable server message (e.g. a UserError) in error.data.message
    _errorMessage(error) {
        return (error && error.data && error.data.message) || (error && error.message) || String(error);
    }

    async onPrintPDF() {
        try {
            const options = {
                move_type: this.state.move_type,
                date_from: this.state.date_from,
                date_to: this.state.date_to,
                partner_ids: this.state.partner_ids,
                analytic_account_ids: this.state.analytic_account_ids,
                only_due: this.state.only_due,
                due_filter: this.state.due_filter,
                show_grand_total: this.state.show_grand_total,
                show_address: this.state.show_address,
                company_id: this.state.company_id,
                currency_opts: this._getCurrencyOptsPayload(),
                // Same text as the search box: print / export only what is shown.
                search_query: (this.state.searchQuery || "").trim(),
            };
            const action = await this.orm.call(
                "due.report.wizard",
                "get_pdf_report_action",
                [],
                { options }
            );
            if (action) {
                await this.action.doAction(action);
            }
        } catch (error) {
            console.error("Failed to print PDF report", error);
            this.notification.add("Failed to generate PDF: " + this._errorMessage(error), {
                type: "danger",
            });
        }
    }

    async onExportXLSX() {
        try {
            const options = {
                move_type: this.state.move_type,
                date_from: this.state.date_from,
                date_to: this.state.date_to,
                partner_ids: this.state.partner_ids,
                analytic_account_ids: this.state.analytic_account_ids,
                only_due: this.state.only_due,
                due_filter: this.state.due_filter,
                show_grand_total: this.state.show_grand_total,
                show_address: this.state.show_address,
                company_id: this.state.company_id,
                currency_opts: this._getCurrencyOptsPayload(),
                // Same text as the search box: print / export only what is shown.
                search_query: (this.state.searchQuery || "").trim(),
            };
            const result = await this.orm.call(
                "due.report.wizard",
                "export_xlsx",
                [],
                { options }
            );
            if (result && result.filecontent) {
                const link = document.createElement("a");
                link.href = "data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64," + result.filecontent;
                link.download = result.filename || "Due_Report.xlsx";
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            }
        } catch (error) {
            console.error("Failed to export Excel report", error);
            this.notification.add("Failed to generate Excel: " + this._errorMessage(error), {
                type: "danger",
            });
        }
    }

    openInvoice(moveId) {
        if (!moveId) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "account.move",
            res_id: moveId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    // --- Search & Filtering Helpers ---
    get filteredGroups() {
        // The result only depends on the loaded groups, the due filter and the
        // lines already fetched, so it is computed once and reused (it is read
        // many times per render by the KPI cards, grand total and amount
        // formatting). The search text is applied by the server.
        const dueFilter = this.state.due_filter || "all";
        const src = this.state.data.groups || [];
        const version = this.state.linesVersion;
        const cache = this._fgCache;
        if (cache && cache.src === src && cache.dueFilter === dueFilter && cache.version === version) {
            return cache.result;
        }
        const result = this._computeFilteredGroups();
        this._fgCache = { src, dueFilter, version, result };
        return result;
    }

    /** [bucketName, bucket] pairs of a group that the due filter keeps. */
    _bucketsFor(group, dueFilter) {
        const buckets = group.buckets || {};
        const names = dueFilter === "upcoming" ? ["upcoming"]
            : dueFilter === "overdue" ? ["overdue"]
            : ["upcoming", "overdue"];
        return names.filter((n) => buckets[n] && buckets[n].count > 0).map((n) => [n, buckets[n]]);
    }

    _computeFilteredGroups() {
        const dueFilter = this.state.due_filter || "all";
        const groups = this.state.data.groups || [];

        // Everything below comes from the group HEADER sent by the server
        // (subtotals + upcoming / overdue buckets), so the partner totals are
        // right even before the partner's lines are loaded, and always equal
        // the PDF / Excel figures.
        return groups
            .map((group) => {
                if (dueFilter === "all") {
                    if (!group.count) {
                        return null;
                    }
                    return { ...group, lines: group.lines || [] };
                }
                const bucket = (group.buckets || {})[dueFilter];
                if (!bucket || !bucket.count) {
                    return null;
                }
                const wantOverdue = dueFilter === "overdue";
                return {
                    ...group,
                    lines: (group.lines || []).filter((line) => !!line.is_overdue === wantOverdue),
                    count: bucket.count,
                    subtotal_bill_amount: bucket.bill,
                    subtotal_total_amount: bucket.bill,
                    subtotal_paid: bucket.paid,
                    subtotal_balance: bucket.balance,
                    subtotal_upcoming: wantOverdue ? 0 : bucket.balance,
                    subtotal_overdue: wantOverdue ? bucket.balance : 0,
                };
            })
            .filter(Boolean);
    }

    /**
     * Currency of the KPI cards / Grand Total.
     * If every partner that is currently visible uses the same currency
     * (e.g. one partner selected or searched) the totals are shown in THAT
     * partner's currency. Only when several different currencies are visible
     * the server's grand-total currency (company currency) is used.
     */
    get totalsCurrency() {
        return this._singleVisibleCurrency()
            || this.state.data.currency
            || { symbol: "", position: "after" };
    }

    /** The currency shared by all visible partners, or null if they differ. */
    _singleVisibleCurrency() {
        const groups = this.filteredGroups;
        if (!groups.length) {
            return null;
        }
        const first = groups[0].currency;
        if (first && groups.every((g) => g.currency && g.currency.id === first.id)) {
            return first;
        }
        return null;
    }

    /**
     * KPI totals of the visible partners, summed from the partner headers
     * (no lines needed). Amounts of partners in different currencies are taken
     * from the t_* figures, which the server expresses in the grand-total
     * currency, so different currencies are never added together.
     */
    get filteredTotals() {
        const groups = this.filteredGroups;
        const dueFilter = this.state.due_filter || "all";
        const tCurrency = this.totalsCurrency;
        const singleCurrency = !!this._singleVisibleCurrency();
        let invoice_count = 0;
        let partner_count = 0;
        let bill_amount = 0;
        let paid = 0;
        let balance = 0;
        let upcoming_balance = 0;
        let upcoming_count = 0;
        let overdue_balance = 0;
        let overdue_count = 0;

        const pick = (tv, v) => (!singleCurrency && tv !== undefined && tv !== null ? tv : v);

        for (const group of groups) {
            partner_count += 1;
            for (const [name, bucket] of this._bucketsFor(group, dueFilter)) {
                const bBal = Number(pick(bucket.t_balance, bucket.balance)) || 0;
                invoice_count += bucket.count;
                bill_amount += Number(pick(bucket.t_bill, bucket.bill)) || 0;
                paid += Number(pick(bucket.t_paid, bucket.paid)) || 0;
                balance += bBal;
                if (name === "overdue") {
                    overdue_balance += bBal;
                    overdue_count += bucket.count;
                } else {
                    upcoming_balance += bBal;
                    upcoming_count += bucket.count;
                }
            }
        }

        const tDec = (tCurrency && tCurrency.decimal_places != null)
            ? tCurrency.decimal_places : 2;
        const tRnd = (v) => Number((v || 0).toFixed(tDec));
        return {
            invoice_count,
            partner_count,
            bill_amount: tRnd(bill_amount),
            paid: tRnd(paid),
            balance: tRnd(balance),
            upcoming_balance: tRnd(upcoming_balance),
            upcoming_count,
            overdue_balance: tRnd(overdue_balance),
            overdue_count,
        };
    }

    // --- Pagination Getters & Methods ---
    get totalPages() {
        const total = this.filteredGroups.length;
        const size = this.state.pageSize;
        if (size === "all" || size <= 0) return 1;
        return Math.max(1, Math.ceil(total / size));
    }

    get pagedGroups() {
        const groups = this.filteredGroups;
        const size = this.state.pageSize;
        if (size === "all" || size <= 0) {
            return groups;
        }
        // Read-only clamp: never write to the state while rendering.
        const page = Math.min(Math.max(this.state.currentPage, 1), this.totalPages);
        const start = (page - 1) * size;
        return groups.slice(start, start + size);
    }

    get paginationStart() {
        const total = this.filteredGroups.length;
        if (total === 0) return 0;
        const size = this.state.pageSize;
        if (size === "all") return 1;
        return (this.state.currentPage - 1) * size + 1;
    }

    get paginationEnd() {
        const total = this.filteredGroups.length;
        const size = this.state.pageSize;
        if (size === "all") return total;
        return Math.min(this.state.currentPage * size, total);
    }

    setPage(page) {
        const p = Math.max(1, Math.min(page, this.totalPages));
        this.state.currentPage = p;
    }

    setPageSize(size) {
        if (size === "all") {
            this.state.pageSize = "all";
        } else {
            this.state.pageSize = parseInt(size, 10) || 20;
        }
        this.state.currentPage = 1;
    }

    get availablePartners() {
        const term = (this.state.partnerSearch || "").trim().toLowerCase();
        const list = this.state.data.partners_list || [];
        if (!term) return list;
        return list.filter((p) => (p.display_name || "").toLowerCase().includes(term));
    }

    getSelectedPartnerObjects() {
        const ids = new Set(this.state.partner_ids);
        return (this.state.data.partners_list || []).filter((p) => ids.has(p.id));
    }

    isPartnerSelected(partnerId) {
        return this.state.partner_ids.includes(partnerId);
    }

    togglePartner(partnerId) {
        const idx = this.state.partner_ids.indexOf(partnerId);
        if (idx === -1) {
            this.state.partner_ids.push(partnerId);
        } else {
            this.state.partner_ids.splice(idx, 1);
        }
        this.loadReportData();
    }

    removePartner(partnerId) {
        const idx = this.state.partner_ids.indexOf(partnerId);
        if (idx !== -1) {
            this.state.partner_ids.splice(idx, 1);
            this.loadReportData();
        }
    }

    clearPartners() {
        if (this.state.partner_ids.length > 0) {
            this.state.partner_ids = [];
            this.loadReportData();
        }
    }

    togglePartnerDropdown() {
        this.state.isPartnerDropdownOpen = !this.state.isPartnerDropdownOpen;
        if (this.state.isPartnerDropdownOpen) {
            this.state.isAnalyticDropdownOpen = false;
        }
    }

    closePartnerDropdown() {
        this.state.isPartnerDropdownOpen = false;
    }

    // --- Analytic Account Selection Helpers ---
    get availableAnalytics() {
        const term = (this.state.analyticSearch || "").trim().toLowerCase();
        const list = this.state.data.analytics_list || [];
        if (!term) return list;
        return list.filter((a) => (a.display_name || a.name || "").toLowerCase().includes(term));
    }

    getSelectedAnalyticObjects() {
        const ids = new Set(this.state.analytic_account_ids);
        return (this.state.data.analytics_list || []).filter((a) => ids.has(a.id));
    }

    isAnalyticSelected(analyticId) {
        return this.state.analytic_account_ids.includes(analyticId);
    }

    toggleAnalytic(analyticId) {
        const idx = this.state.analytic_account_ids.indexOf(analyticId);
        if (idx === -1) {
            this.state.analytic_account_ids.push(analyticId);
        } else {
            this.state.analytic_account_ids.splice(idx, 1);
        }
        this.loadReportData();
    }

    removeAnalytic(analyticId) {
        const idx = this.state.analytic_account_ids.indexOf(analyticId);
        if (idx !== -1) {
            this.state.analytic_account_ids.splice(idx, 1);
            this.loadReportData();
        }
    }

    clearAnalytics() {
        if (this.state.analytic_account_ids.length > 0) {
            this.state.analytic_account_ids = [];
            this.loadReportData();
        }
    }

    toggleAnalyticDropdown() {
        this.state.isAnalyticDropdownOpen = !this.state.isAnalyticDropdownOpen;
        if (this.state.isAnalyticDropdownOpen) {
            this.state.isPartnerDropdownOpen = false;
        }
    }

    closeAnalyticDropdown() {
        this.state.isAnalyticDropdownOpen = false;
    }

    // --- Collapsible Groups (lines are loaded from the server when opened) ---
    isGroupCollapsed(partnerId) {
        return !this.state.expandedGroupIds.includes(partnerId);
    }

    async toggleGroupCollapse(partnerId) {
        const idx = this.state.expandedGroupIds.indexOf(partnerId);
        if (idx !== -1) {
            this.state.expandedGroupIds.splice(idx, 1);
            return;
        }
        await this._expandGroups([partnerId]);
    }

    /** Opens the partners of the current page (at most MAX_EXPAND_ALL). */
    async expandAll() {
        let ids = this.pagedGroups.map((g) => g.partner_id);
        if (ids.length > MAX_EXPAND_ALL) {
            ids = ids.slice(0, MAX_EXPAND_ALL);
            this.notification.add(
                `Only the first ${MAX_EXPAND_ALL} partners of this page were opened. Use a smaller page size or search to narrow the list.`,
                { type: "info" }
            );
        }
        await this._expandGroups(ids);
    }

    collapseAll() {
        this.state.expandedGroupIds = [];
    }

    // --- Currency Filter ---
    get currencyFilterLabel() {
        return this.state.conversionApplied && this.state.selectedCurrencyName
            ? this.state.selectedCurrencyName
            : "Currency";
    }

    toggleCurrencyDropdown() {
        this.state.isCurrencyDropdownOpen = !this.state.isCurrencyDropdownOpen;
        if (this.state.isCurrencyDropdownOpen) {
            this.state.isPartnerDropdownOpen = false;
            this.state.isAnalyticDropdownOpen = false;
        }
    }

    closeCurrencyDropdown() {
        this.state.isCurrencyDropdownOpen = false;
    }

    onCurrencySelect(currency) {
        this.state.selectedCurrencyId = currency.id;
        this.state.selectedCurrencyName = currency.name;
        this.state.selectedCurrencySymbol = currency.symbol;
        // A new currency invalidates any rate the user had already typed.
        this.state.customRates = {};
        this.state.customRateInverted = {};
    }

    /**
     * Currencies the listed documents were issued in, except the selected
     * currency itself (those documents keep their own amounts and need no
     * rate). One "1 EUR = [rate] SAR" input is shown per entry.
     */
    get customRateCurrencies() {
        const selectedId = this.state.selectedCurrencyId;
        return (this.state.data.transaction_currencies || []).filter((c) => c.id !== selectedId);
    }

    onRateInput(currencyId, ev) {
        this.state.customRates[currencyId] = ev.target.value;
    }

    _currencyById(id) {
        return (this.state.currencies || []).find((c) => c.id === id);
    }

    _fmtRate(value) {
        return Number(Number(value).toPrecision(6)).toString();
    }

    /**
     * One entry per "1 X = [rate] Y" input of the Custom Rate section.
     * Default direction: 1 <transaction currency> = rate <selected currency>.
     * The swap button flips it to 1 <selected currency> = rate <transaction currency>.
     */
    get customRateRows() {
        const selected = this._currencyById(this.state.selectedCurrencyId) || {};
        const selectedName = this.state.selectedCurrencyName;
        return this.customRateCurrencies.map((tc) => {
            const inverted = !!this.state.customRateInverted[tc.id];
            const left = inverted ? selectedName : tc.name;
            const right = inverted ? tc.name : selectedName;
            const typed = parseFloat(this.state.customRates[tc.id]);

            // Current system rate, in the direction shown on this row.
            const from = this._currencyById(tc.id);
            let current = 0;
            if (from && from.rate > 0 && selected.rate > 0) {
                const perTransactionUnit = selected.rate / from.rate; // 1 tc = x selected
                current = inverted ? 1 / perTransactionUnit : perTransactionUnit;
            }
            return {
                id: tc.id,
                left,
                right,
                value: this.state.customRates[tc.id] ?? "",
                placeholder: current ? this._fmtRate(current) : "Rate",
                // Reverse reading of what was typed, so a backwards rate is obvious.
                hint: typed > 0 ? `= 1 ${right} = ${this._fmtRate(1 / typed)} ${left}` : "",
                currentText: current ? this._fmtRate(current) : "",
            };
        });
    }

    swapRateDirection(currencyId) {
        const typed = parseFloat(this.state.customRates[currencyId]);
        this.state.customRateInverted[currencyId] = !this.state.customRateInverted[currencyId];
        // Keep the same meaning: show the reciprocal of the number already typed.
        if (typed > 0) {
            this.state.customRates[currencyId] = this._fmtRate(1 / typed);
        }
    }

    useCurrentRate(currencyId) {
        const row = this.customRateRows.find((r) => r.id === currencyId);
        if (row && row.currentText) {
            this.state.customRates[currencyId] = row.currentText;
        }
    }

    toggleTransactionRates() {
        this.state.useTransactionRates = true;
    }

    selectCustomRateMode() {
        this.state.useTransactionRates = false;
    }

    async applyCurrencyConversion() {
        if (!this.state.selectedCurrencyId) {
            this.notification.add("Please select a currency first.", { type: "warning" });
            return;
        }
        if (!this.state.useTransactionRates) {
            for (const row of this.customRateRows) {
                const rate = parseFloat(row.value);
                if (!rate || rate <= 0) {
                    this.notification.add(
                        `Please enter the rate for 1 ${row.left} in ${row.right}.`,
                        { type: "warning" }
                    );
                    return;
                }
            }
        }
        this.state.conversionApplied = true;
        this.state.isCurrencyDropdownOpen = false;
        await this.loadReportData();
    }

    async resetCurrencyConversion() {
        this.state.conversionApplied = false;
        this.state.selectedCurrencyId = null;
        this.state.selectedCurrencyName = "";
        this.state.selectedCurrencySymbol = "";
        this.state.customRates = {};
        this.state.customRateInverted = {};
        this.state.useTransactionRates = true;
        this.state.isCurrencyDropdownOpen = false;
        // Back to the default: each partner in its own currency.
        await this.loadReportData();
    }

    // --- Date presets ---
    setPreset(preset) {
        const now = new Date();
        const y = now.getFullYear();
        const m = now.getMonth();

        if (preset === "this_month") {
            const first = new Date(y, m, 1);
            const last = new Date(y, m + 1, 0);
            this.state.date_from = this.formatDateISO(first);
            this.state.date_to = this.formatDateISO(last);
        } else if (preset === "this_quarter") {
            const q = Math.floor(m / 3);
            const first = new Date(y, q * 3, 1);
            const last = new Date(y, (q + 1) * 3, 0);
            this.state.date_from = this.formatDateISO(first);
            this.state.date_to = this.formatDateISO(last);
        } else if (preset === "this_year") {
            this.state.date_from = `${y}-01-01`;
            this.state.date_to = `${y}-12-31`;
        } else if (preset === "all") {
            this.state.date_from = "";
            this.state.date_to = "";
        }
        this.loadReportData();
    }

    formatDateISO(d) {
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, "0");
        const day = String(d.getDate()).padStart(2, "0");
        return `${y}-${m}-${day}`;
    }

    formatDisplayDate(isoDate) {
        if (!isoDate) return "";
        const parts = isoDate.split("-");
        if (parts.length === 3) {
            return `${parts[2]}/${parts[1]}/${parts[0]}`;
        }
        return isoDate;
    }

    /**
     * Format an amount with a currency symbol.
     * @param {Number} amt
     * @param {Object} [currency] {symbol, position, decimal_places}. Pass the
     *   partner group's `currency` for rows / partner totals. Omit it for the
     *   KPI cards and grand total (they use state.data.currency).
     */
    formatAmount(amt, currency) {
        // No currency given -> KPI cards / Grand Total: use the currency of the
        // visible partners (or the grand-total currency when they differ).
        const cur = currency || this.totalsCurrency || { symbol: "", position: "after" };
        const decimals = Number.isInteger(cur.decimal_places) ? cur.decimal_places : 2;
        const val = Number(amt) || 0;
        const formatted = Math.abs(val).toLocaleString(undefined, {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals,
        });
        const prefix = val < 0 ? "-" : "";
        if (cur.position === "before") {
            return `${prefix}${cur.symbol || ""} ${formatted}`.trim();
        }
        return `${prefix}${formatted} ${cur.symbol || ""}`.trim();
    }
}

registry.category("actions").add("custom_due_reports.DueReportView", DueReportView);