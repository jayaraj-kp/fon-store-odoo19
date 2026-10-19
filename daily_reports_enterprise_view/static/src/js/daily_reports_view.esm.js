/** @odoo-module **/

import { Component, useState, markRaw, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

// Rendering limits: keep the DOM small even when 5000 lines are loaded.
const INITIAL_ROWS = 200; // children rendered when a group is first expanded
const MORE_ROWS = 500; // added every time "Show more" is clicked
const AUTO_EXPAND_MAX_LINES = 150; // small reports open fully expanded

export class DailyReportsView extends Component {
    static template = "daily_reports_enterprise_view.DailyReportsView";
    static props = ["*"];

    setup() {
        this.actionService = useService("action");
        this.notification = useService("notification");

        const params = this.props.action.params || {};
        this.reportType = params.report_type || "cash_book";
        this.reportTitle = params.title || "Daily Report";
        this.companyId = null;

        const today = new Date();
        // built from local parts (toISOString() shifts the date by timezone)
        const firstDay = `${today.getFullYear()}-01-01`;
        const lastDay = `${today.getFullYear()}-12-31`;

        this.state = useState({
            reportType: this.reportType,
            reportTitle: this.reportTitle,
            dateFrom: firstDay,
            dateTo: lastDay,
            targetMove: "posted",
            loading: false,
            dataLoaded: false,
            lines: [],
            currencySymbol: "",
            openDropdown: null,
            expandedGroups: new Set(),
            visible: {}, // groupId -> number of children rendered
            darkMode: true,

            // Top search bar
            searchTerm: "",
            topSearchResults: [],
            topSearchOpen: false,

            // Partner filter
            selectedPartners: [],
            partnerSearchTerm: "",
            partnerSearchResults: [],

            // Analytic filter
            selectedAnalytics: [],
            allAnalytics: [],
            analyticSearchTerm: "",
            analyticSearchResults: [],
        });

        this.moreRows = MORE_ROWS;
        this._reqId = 0;
        this._exporting = false;
        this._topSearchDebounce = null;
        this._partnerSearchDebounce = null;
        this._analyticSearchDebounce = null;
        this._docClickHandler = this._onDocClick.bind(this);

        onWillStart(async () => {
            await this.loadInitData();
        });

        onMounted(() => {
            document.addEventListener("click", this._docClickHandler);
        });

        onWillUnmount(() => {
            document.removeEventListener("click", this._docClickHandler);
            clearTimeout(this._topSearchDebounce);
            clearTimeout(this._partnerSearchDebounce);
            clearTimeout(this._analyticSearchDebounce);
        });
    }

    _onDocClick() {
        this.state.topSearchOpen = false;
        this.state.openDropdown = null;
    }

    _errorMessage(e) {
        return (
            (e && e.data && e.data.message) ||
            (e && e.message) ||
            _t("Unexpected error. Please try again.")
        );
    }

    _notifyError(e) {
        console.error("Daily reports error:", e);
        this.notification.add(this._errorMessage(e), { type: "danger", sticky: true });
    }

    _params() {
        return {
            report_type: this.state.reportType,
            company_id: this.companyId,
            date_from: this.state.dateFrom,
            date_to: this.state.dateTo,
            target_move: this.state.targetMove,
            partner_ids: this.state.selectedPartners.map((p) => p.id),
            analytic_account_ids: this.state.selectedAnalytics.map((a) => a.id),
        };
    }

    async loadInitData() {
        try {
            const init = await rpc("/dr/init", {});
            this.companyId = init.company_id || null;
            if (init.date_from) {
                this.state.dateFrom = init.date_from;
            }
            if (init.date_to) {
                this.state.dateTo = init.date_to;
            }
            if (init.currency_symbol) {
                this.state.currencySymbol = init.currency_symbol;
            }
        } catch (e) {
            console.error("Error loading init data:", e);
        }
    }

    async loadData() {
        if (!this.state.dateFrom || !this.state.dateTo) {
            this.notification.add(_t("Please select both dates."), { type: "warning" });
            return;
        }
        const reqId = ++this._reqId;
        this.state.loading = true;
        try {
            const res = await rpc("/dr/get_data", this._params());
            if (reqId !== this._reqId) {
                return; // a newer request was started, ignore this answer
            }
            // lines are read-only: markRaw avoids creating thousands of reactive proxies
            this.state.lines = markRaw(res.lines || []);
            this.state.currencySymbol = res.show_balance === false ? "" : res.currency_symbol || "";
            if (res.report_title) {
                this.state.reportTitle = res.report_title;
            }
            // Groups start COLLAPSED (their totals stay visible). Only small
            // reports are opened automatically; big ones never render 5000 rows at once.
            const newExpanded = new Set();
            if ((res.shown_lines || 0) <= AUTO_EXPAND_MAX_LINES) {
                for (const line of this.state.lines) {
                    if (line.id && line.children && line.children.length) {
                        newExpanded.add(line.id);
                    }
                }
            }
            this.state.expandedGroups = newExpanded;
            this.state.visible = {};
            this.state.dataLoaded = true;

            if (res.truncated) {
                this.notification.add(
                    _t(
                        "Showing the first %(shown)s of %(total)s lines. Totals and balances are complete and correct. Narrow the filters to see every line, or use Excel export.",
                        { shown: res.shown_lines, total: res.total_lines }
                    ),
                    { type: "warning", sticky: true }
                );
            }
            if (res.integrity_ok === false) {
                this.notification.add(
                    _t("Balance check failed: ") + (res.integrity_messages || []).join(" | "),
                    { type: "danger", sticky: true }
                );
            }
        } catch (e) {
            if (reqId === this._reqId) {
                this._notifyError(e);
            }
        } finally {
            if (reqId === this._reqId) {
                this.state.loading = false;
            }
        }
    }

    async onApplyFilters() {
        this.state.topSearchOpen = false;
        this.state.openDropdown = null;
        await this.loadData();
    }

    get totalRow() {
        return this.state.lines.find((l) => l.line_type === "total");
    }

    get displayedLines() {
        return this.state.lines.filter((l) => l.line_type !== "total");
    }

    get dateLabel() {
        return `${this.fmtDate(this.state.dateFrom)} - ${this.fmtDate(this.state.dateTo)}`;
    }

    get partnersFilterLabel() {
        const count = this.state.selectedPartners.length;
        return count ? `Customer/Vendor (${count})` : "Customer/Vendor";
    }

    get analyticsFilterLabel() {
        const count = this.state.selectedAnalytics.length;
        return count ? `Analytic (${count})` : "Analytic";
    }

    toggleGroup(id) {
        if (this.state.expandedGroups.has(id)) {
            this.state.expandedGroups.delete(id);
        } else {
            this.state.expandedGroups.add(id);
        }
    }

    isExpanded(id) {
        return this.state.expandedGroups.has(id);
    }

    // --- progressive rendering of the children of an expanded group ---
    _visibleLimit(line) {
        return this.state.visible[line.id] || INITIAL_ROWS;
    }

    visibleChildren(line) {
        const children = line.children || [];
        return children.slice(0, this._visibleLimit(line));
    }

    hiddenCount(line) {
        const total = (line.children || []).length;
        return Math.max(0, total - this._visibleLimit(line));
    }

    showMore(id) {
        const line = this.state.lines.find((l) => l.id === id);
        if (line) {
            this.state.visible[id] = this._visibleLimit(line) + MORE_ROWS;
        }
    }

    toggleDropdown(name, e) {
        e.stopPropagation();
        const was = this.state.openDropdown;
        this.state.topSearchOpen = false;
        this.state.openDropdown = was === name ? null : name;
        if (this.state.openDropdown === "analytics" && !this.state.allAnalytics.length) {
            this._loadAllAnalytics();
        }
    }

    setTargetMove(val) {
        this.state.targetMove = val;
        this.state.openDropdown = null;
    }

    onDateFromChange(ev) {
        this.state.dateFrom = ev.target.value;
    }

    onDateToChange(ev) {
        this.state.dateTo = ev.target.value;
    }

    // --- Top search bar (searches customers/vendors) ---
    onTopSearchInput(ev) {
        this.state.searchTerm = ev.target.value;
        clearTimeout(this._topSearchDebounce);
        const term = this.state.searchTerm.trim();
        if (!term) {
            this.state.topSearchResults = [];
            this.state.topSearchOpen = false;
            return;
        }
        this.state.topSearchOpen = true;
        this._topSearchDebounce = setTimeout(async () => {
            try {
                const results = await rpc("/dr/search_partners", { term });
                this.state.topSearchResults = results || [];
            } catch (e) {
                console.error("Top search error:", e);
            }
        }, 250);
    }

    onTopSearchFocus() {
        if (this.state.searchTerm.trim() && this.state.topSearchResults.length) {
            this.state.topSearchOpen = true;
        }
    }

    onTopSearchKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this._selectTopSearchResults();
        } else if (ev.key === "Escape") {
            this.state.topSearchOpen = false;
        }
    }

    selectTopSearchResult(partner) {
        this._addPartnerToList(partner);
        this.state.searchTerm = "";
        this.state.topSearchResults = [];
        this.state.topSearchOpen = false;
        this.loadData();
    }

    _selectTopSearchResults() {
        for (const p of this.state.topSearchResults) {
            this._addPartnerToList(p);
        }
        this.state.searchTerm = "";
        this.state.topSearchResults = [];
        this.state.topSearchOpen = false;
        this.loadData();
    }

    clearTopSearch() {
        this.state.searchTerm = "";
        this.state.topSearchResults = [];
        this.state.topSearchOpen = false;
    }

    // --- Partner filter dropdown search ---
    async onPartnerSearchInput(ev) {
        this.state.partnerSearchTerm = ev.target.value;
        clearTimeout(this._partnerSearchDebounce);
        if (!this.state.partnerSearchTerm.trim()) {
            this.state.partnerSearchResults = [];
            return;
        }
        this._partnerSearchDebounce = setTimeout(async () => {
            try {
                const results = await rpc("/dr/search_partners", {
                    term: this.state.partnerSearchTerm,
                });
                this.state.partnerSearchResults = results || [];
            } catch (e) {
                console.error("Partner search error:", e);
            }
        }, 250);
    }

    addPartner(partner) {
        this._addPartnerToList(partner);
        this.state.partnerSearchTerm = "";
        this.state.partnerSearchResults = [];
    }

    _addPartnerToList(partner) {
        if (!this.state.selectedPartners.find((p) => p.id === partner.id)) {
            this.state.selectedPartners.push({ id: partner.id, name: partner.name });
        }
    }

    removePartner(partnerId) {
        this.state.selectedPartners = this.state.selectedPartners.filter(
            (p) => p.id !== partnerId
        );
    }

    // --- Analytic filter ---
    async _loadAllAnalytics() {
        try {
            const results = await rpc("/dr/search_analytics", { term: "" });
            this.state.allAnalytics = results || [];
        } catch (e) {
            console.error("Load all analytics error:", e);
        }
    }

    async onAnalyticSearchInput(ev) {
        this.state.analyticSearchTerm = ev.target.value;
        clearTimeout(this._analyticSearchDebounce);
        if (!this.state.analyticSearchTerm.trim()) {
            this.state.analyticSearchResults = [];
            return;
        }
        this._analyticSearchDebounce = setTimeout(async () => {
            try {
                const results = await rpc("/dr/search_analytics", {
                    term: this.state.analyticSearchTerm,
                });
                this.state.analyticSearchResults = results || [];
            } catch (e) {
                console.error("Analytic search error:", e);
            }
        }, 250);
    }

    isAnalyticSelected(analyticId) {
        return this.state.selectedAnalytics.some((a) => a.id === analyticId);
    }

    toggleAnalytic(analytic) {
        if (this.isAnalyticSelected(analytic.id)) {
            this.state.selectedAnalytics = this.state.selectedAnalytics.filter(
                (a) => a.id !== analytic.id
            );
        } else {
            this.state.selectedAnalytics.push({ id: analytic.id, name: analytic.name });
        }
    }

    addAnalytic(analytic) {
        if (!this.state.selectedAnalytics.find((a) => a.id === analytic.id)) {
            this.state.selectedAnalytics.push({ id: analytic.id, name: analytic.name });
        }
        this.state.analyticSearchTerm = "";
        this.state.analyticSearchResults = [];
    }

    removeAnalytic(analyticId) {
        this.state.selectedAnalytics = this.state.selectedAnalytics.filter(
            (a) => a.id !== analyticId
        );
    }

    openMove(moveId) {
        if (!moveId) {
            return;
        }
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "account.move",
            res_id: moveId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    // --- Exports ---
    _base64ToBlob(b64, type) {
        const bytes = atob(b64);
        const arr = new Uint8Array(bytes.length);
        for (let i = 0; i < bytes.length; i++) {
            arr[i] = bytes.charCodeAt(i);
        }
        return new Blob([arr], { type });
    }

    _download(blob, fileName) {
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = fileName;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        setTimeout(() => URL.revokeObjectURL(url), 10000);
    }

    async onPrintPdf() {
        if (this._exporting) {
            return;
        }
        this._exporting = true;
        // open the tab synchronously (inside the click) so popup blockers allow it
        const win = window.open("", "_blank");
        try {
            const res = await rpc("/dr/export_pdf", this._params());
            if (res && res.file_content) {
                const blob = this._base64ToBlob(res.file_content, "application/pdf");
                if (win) {
                    win.location.href = URL.createObjectURL(blob);
                } else {
                    this._download(blob, res.file_name || "daily_report.pdf");
                }
            } else if (win) {
                win.close();
            }
        } catch (e) {
            if (win) {
                win.close();
            }
            this._notifyError(e);
        } finally {
            this._exporting = false;
        }
    }

    async onExportExcel() {
        if (this._exporting) {
            return;
        }
        this._exporting = true;
        try {
            // Build query-string from current filter state.
            // partner_ids / analytic_account_ids are sent as comma-separated
            // values so the HTTP GET route can parse them.
            const p = this._params();
            const qs = new URLSearchParams();
            qs.set("report_type", p.report_type || "cash_book");
            if (p.company_id) qs.set("company_id", String(p.company_id));
            if (p.date_from)  qs.set("date_from",  p.date_from);
            if (p.date_to)    qs.set("date_to",    p.date_to);
            qs.set("target_move", p.target_move || "posted");
            if (p.partner_ids && p.partner_ids.length) {
                qs.set("partner_ids", p.partner_ids.join(","));
            }
            if (p.analytic_account_ids && p.analytic_account_ids.length) {
                qs.set("analytic_account_ids", p.analytic_account_ids.join(","));
            }

            // Use fetch() instead of <a download> so we can detect server errors.
            // <a download> silently ignores non-200 responses — the user sees
            // nothing when an AccessError or "too many lines" UserError occurs.
            const resp = await fetch("/dr/export_excel_stream?" + qs.toString(), {
                method: "GET",
                credentials: "same-origin",
            });

            if (!resp.ok) {
                const ct = resp.headers.get("Content-Type") || "";
                const text = await resp.text();
                let msg = "";
                if (ct.startsWith("text/plain") && text.trim()) {
                    // Plain text: our controller's UserError / AccessError response
                    msg = text.trim();
                } else if (ct.includes("application/json")) {
                    try {
                        const parsed = JSON.parse(text);
                        msg = parsed?.error?.data?.message ||
                              parsed?.error?.message ||
                              parsed?.message || "";
                    } catch (_) {
                        // ignore JSON parse error
                    }
                }
                // If HTML (e.g. 500 error / nginx proxy 502/504) or empty, avoid dumping raw HTML
                if (!msg) {
                    msg = _t("Excel export failed (server error %(status)s).", { status: resp.status });
                }
                this.notification.add(msg, { type: "danger", sticky: true });
                return;
            }

            // Success: stream the response into a Blob and trigger download.
            const buffer = await resp.arrayBuffer();
            const blob = new Blob([buffer], {
                type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            });
            // Derive the filename from Content-Disposition if the server sent one.
            let fileName = "daily_report.xlsx";
            const cd = resp.headers.get("Content-Disposition") || "";
            const utf8Match = cd.match(/filename\*=UTF-8''([^;\n]+)/i);
            const standardMatch = cd.match(/filename=["']?([^"';\n]+)["']?/i);
            if (utf8Match && utf8Match[1]) {
                fileName = decodeURIComponent(utf8Match[1].trim());
            } else if (standardMatch && standardMatch[1]) {
                fileName = standardMatch[1].trim();
            }
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = fileName;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            // Revoke the object URL after the browser has had time to start the download.
            setTimeout(() => URL.revokeObjectURL(url), 30000);
        } catch (e) {
            this._notifyError(e);
        } finally {
            // Small delay so the button stays disabled while the download begins.
            setTimeout(() => { this._exporting = false; }, 2000);
        }
    }


    // --- Close report and return to the Apps dashboard ---
    onClose() {
        window.location.href = "/odoo";
    }

    fmtDate(d) {
        if (!d) {
            return "";
        }
        const parts = d.split("-");
        if (parts.length === 3) {
            return `${parts[2]}/${parts[1]}/${parts[0]}`;
        }
        return d;
    }

    fmtNum(val) {
        if (val === null || val === undefined) {
            return ""; // Day Book has no running balance
        }
        return Number(val).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    toggleTheme() {
        this.state.darkMode = !this.state.darkMode;
    }
}

registry.category("actions").add("daily_reports_view", DailyReportsView);