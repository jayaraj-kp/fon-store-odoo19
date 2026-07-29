///**
// * BAK Balance Sheet Inline Report – Client JS
// * Handles: filter application, data fetch from JSON endpoint,
// *          dynamic HTML rendering, PDF/XLSX download, expand/collapse.
// */
//(function () {
//    'use strict';
//
//    // ── DOM helpers ────────────────────────────────────────────
//    const $ = (sel, ctx) => (ctx || document).querySelector(sel);
//    const $$ = (sel, ctx) => [...(ctx || document).querySelectorAll(sel)];
//    const el = (tag, cls, html) => {
//        const e = document.createElement(tag);
//        if (cls) e.className = cls;
//        if (html !== undefined) e.innerHTML = html;
//        return e;
//    };
//
//    // ── State ──────────────────────────────────────────────────
//    const app = document.getElementById('bak_bs_app');
//    if (!app) return;
//
//    const state = {
//        wizardId:    app.dataset.wizardId,
//        dateTo:      app.dataset.dateTo || '',
//        dateFrom:    app.dataset.dateFrom || '',
//        targetMove:  app.dataset.targetMove || 'posted',
//        showDC:      app.dataset.displayDc === 'true',
//        comparison:  false,
//        compDateTo:  '',
//        compDateFrom:'',
//        analyticIds: [],
//    };
//
//    // ── Wire up filter controls ─────────────────────────────────
//    function initControls() {
//        $('#flt_date_to').value  = state.dateTo;
//        $('#flt_date_from').value = state.dateFrom;
//        $('#chk_dc').checked     = state.showDC;
//        $('#sel_moves').value    = state.targetMove;
//
//        $('#btn_apply').addEventListener('click', applyFilters);
//        $('#btn_pdf').addEventListener('click', downloadPDF);
//        $('#btn_xlsx').addEventListener('click', downloadXLSX);
//        $('#btn_comparison').addEventListener('click', toggleComparison);
//
//        // Enter key on date inputs
//        ['flt_date_to','flt_date_from','flt_comp_date_to','flt_comp_date_from'].forEach(id => {
//            const inp = document.getElementById(id);
//            if (inp) inp.addEventListener('keydown', e => { if (e.key === 'Enter') applyFilters(); });
//        });
//
//        // Dropdown toggle listener
//        const dropdownBtn = $('#analytic_dropdown_btn');
//        const dropdownContent = $('#analytic_dropdown_content');
//        if (dropdownBtn && dropdownContent) {
//            dropdownBtn.addEventListener('click', (e) => {
//                e.stopPropagation();
//                const show = dropdownContent.style.display === 'none';
//                dropdownContent.style.display = show ? 'block' : 'none';
//            });
//            document.addEventListener('click', (e) => {
//                if (!dropdownContent.contains(e.target) && e.target !== dropdownBtn) {
//                    dropdownContent.style.display = 'none';
//                }
//            });
//        }
//    }
//
//    function toggleComparison() {
//        state.comparison = !state.comparison;
//        $('#btn_comparison').classList.toggle('active', state.comparison);
//        $('#grp_comparison').style.display      = state.comparison ? '' : 'none';
//        $('#grp_comparison_from').style.display = state.comparison ? '' : 'none';
//    }
//
//    // ── Apply filters → fetch data ──────────────────────────────
//    function applyFilters() {
//        state.dateTo      = $('#flt_date_to').value;
//        state.dateFrom    = $('#flt_date_from').value;
//        state.showDC      = $('#chk_dc').checked;
//        state.targetMove  = $('#sel_moves').value;
//        state.compDateTo  = $('#flt_comp_date_to') ? $('#flt_comp_date_to').value : '';
//        state.compDateFrom= $('#flt_comp_date_from') ? $('#flt_comp_date_from').value : '';
//        fetchReport();
//    }
//
//    // ── JSON RPC call ───────────────────────────────────────────
//    async function fetchReport() {
//        showLoading();
//        try {
//            const body = {
//                jsonrpc: '2.0',
//                method: 'call',
//                id: 1,
//                params: {
//                    wizard_id:          state.wizardId,
//                    date_to:            state.dateTo || null,
//                    date_from:          state.dateFrom || null,
//                    target_move:        state.targetMove,
//                    display_debit_credit: state.showDC,
//                    enable_comparison:  state.comparison,
//                    comparison_date_to: state.compDateTo || null,
//                    comparison_date_from: state.compDateFrom || null,
//                    analytic_ids:       state.analyticIds || [],
//                },
//            };
//            const res  = await fetch('/bak/balance_sheet/data', {
//                method:  'POST',
//                headers: { 'Content-Type': 'application/json' },
//                body:    JSON.stringify(body),
//            });
//            const json = await res.json();
//            if (json.error) {
//                showError(json.error.data?.message || 'Server error');
//                return;
//            }
//            renderReport(json.result);
//        } catch (err) {
//            showError('Network error: ' + err.message);
//        }
//    }
//
//    // ── Fetch and initialize Analytic Accounts ─────────────────
//    async function loadAnalyticAccounts() {
//        try {
//            const body = {
//                jsonrpc: '2.0',
//                method: 'call',
//                id: 2,
//                params: {},
//            };
//            const res = await fetch('/bak/balance_sheet/analytic_accounts', {
//                method: 'POST',
//                headers: { 'Content-Type': 'application/json' },
//                body: JSON.stringify(body),
//            });
//            const json = await res.json();
//            if (json.result) {
//                renderAnalyticDropdown(json.result);
//            }
//        } catch (e) {
//            console.error("Failed to load analytic accounts:", e);
//        }
//    }
//
//    function renderAnalyticDropdown(accounts) {
//        const list = $('#analytic_items_list');
//        if (!list) return;
//        list.innerHTML = '';
//
//        accounts.forEach(acc => {
//            const item = el('label', 'bak-dropdown-item');
//            item.innerHTML = `<input type="checkbox" data-id="${acc.id}" value="${acc.name}"/> <span>${acc.name}</span>`;
//            list.appendChild(item);
//        });
//
//        const btn = $('#analytic_dropdown_btn');
//        const checkboxes = $$('#analytic_items_list input[type="checkbox"]');
//
//        checkboxes.forEach(chk => {
//            chk.addEventListener('change', () => {
//                const selected = checkboxes.filter(c => c.checked);
//                state.analyticIds = selected.map(c => parseInt(c.dataset.id));
//                if (selected.length === 0) {
//                    btn.innerText = 'Select Analytic Accounts...';
//                } else if (selected.length === 1) {
//                    btn.innerText = selected[0].value;
//                } else {
//                    btn.innerText = `${selected.length} Selected`;
//                }
//            });
//        });
//
//        const searchInput = $('#analytic_search');
//        if (searchInput) {
//            searchInput.addEventListener('input', (e) => {
//                const q = e.target.value.toLowerCase();
//                const items = $$('.bak-dropdown-item', list);
//                items.forEach(item => {
//                    const text = item.querySelector('span').innerText.toLowerCase();
//                    item.style.display = text.includes(q) ? '' : 'none';
//                });
//            });
//        }
//    }
//
//    // ── Render ──────────────────────────────────────────────────
//    function renderReport(data) {
//        const wrap = document.getElementById('bak_report_content');
//        wrap.innerHTML = '';
//
//        const showDC   = data.display_debit_credit;
//        const showComp = data.enable_comparison;
//        const sym      = data.currency_symbol || '';
//
//        // Header
//        const hdr = el('div', 'bak-rpt-header');
//        hdr.innerHTML = `
//            <div class="bak-rpt-company">${data.company_name}</div>
//            <div class="bak-rpt-period">
//                As of <strong>${data.date_to}</strong>
//                ${data.date_from ? ' &mdash; From ' + data.date_from : ''}
//                &nbsp;|&nbsp;
//                ${data.target_move === 'posted' ? 'Posted Entries' : 'All Entries'}
//            </div>`;
//        wrap.appendChild(hdr);
//
//        // Table
//        const table = el('table', 'bak-rpt-table');
//
//        // THEAD
//        const thead = el('thead');
//        let headHtml = '<tr><th>Code</th><th>Account</th>';
//        if (showDC)   headHtml += '<th class="num">Debit</th><th class="num">Credit</th>';
//        headHtml += '<th class="num">Balance</th>';
//        if (showComp) headHtml += `<th class="num">As of ${data.comparison_date_to || 'Prev'}</th>`;
//        headHtml += '</tr>';
//        thead.innerHTML = headHtml;
//        table.appendChild(thead);
//
//        const tbody = el('tbody');
//
//        // Helper: format number
//        const fmt = (n) => {
//            if (n === null || n === undefined) return '';
//            const abs = Math.abs(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
//            return (n < 0 ? '-' : '') + sym + ' ' + abs;
//        };
//
//        const appendSection = (title, subsections, total, compTotal) => {
//            // Section header row
//            const secRow = el('tr', 'bak-row-section');
//            const secCols = 2 + (showDC ? 2 : 0) + 1 + (showComp ? 1 : 0);
//            secRow.innerHTML = `
//                <td colspan="${secCols}">
//                    <span class="bak-toggle">&#9660;</span>
//                    ${title.toUpperCase()}
//                </td>`;
//            secRow.addEventListener('click', () => {
//                const collapsed = secRow.classList.toggle('collapsed');
//                // toggle all child rows
//                let sib = secRow.nextElementSibling;
//                while (sib && !sib.classList.contains('bak-row-section') &&
//                       !sib.classList.contains('bak-row-le-total')) {
//                    sib.style.display = collapsed ? 'none' : '';
//                    sib = sib.nextElementSibling;
//                }
//            });
//            tbody.appendChild(secRow);
//
//            subsections.forEach(sub => {
//                // Sub-header
//                const subRow = el('tr', 'bak-row-subsection');
//                subRow.innerHTML = `<td colspan="${secCols}">${sub.name}</td>`;
//                tbody.appendChild(subRow);
//
//                // Account rows
//                (sub.rows || []).forEach(row => {
//                    const accRow = el('tr', 'bak-row-account');
//                    const negClass = row.balance < 0 ? ' negative' : '';
//                    let html = `
//                        <td class="col-code">${row.code || ''}</td>
//                        <td>${row.name}</td>`;
//                    if (showDC) {
//                        html += `
//                        <td class="num"><span class="bak-clickable-amount" data-type="debit" data-acc-id="${row.id}">${fmt(row.debit)}</span></td>
//                        <td class="num"><span class="bak-clickable-amount" data-type="credit" data-acc-id="${row.id}">${fmt(row.credit)}</span></td>`;
//                    }
//                    html += `<td class="num${negClass}"><span class="bak-clickable-amount" data-type="balance" data-acc-id="${row.id}">${fmt(row.balance)}</span></td>`;
//                    if (showComp) {
//                        const cn = row.comp_balance < 0 ? ' negative' : '';
//                        html += `<td class="num${cn}"><span class="bak-clickable-amount" data-type="comp_balance" data-acc-id="${row.id}">${fmt(row.comp_balance)}</span></td>`;
//                    }
//                    accRow.innerHTML = html;
//                    tbody.appendChild(accRow);
//                });
//
//                // Subtotal row
//                const stRow = el('tr', 'bak-row-subtotal');
//                let stHtml = `<td class="col-code"></td><td>Total ${sub.name}</td>`;
//                if (showDC) stHtml += '<td></td><td></td>';
//                const sneg = sub.subtotal < 0 ? ' negative' : '';
//                stHtml += `<td class="num${sneg}">${fmt(sub.subtotal)}</td>`;
//                if (showComp) {
//                    const cn = sub.comp_subtotal < 0 ? ' negative' : '';
//                    stHtml += `<td class="num${cn}">${fmt(sub.comp_subtotal)}</td>`;
//                }
//                stRow.innerHTML = stHtml;
//                tbody.appendChild(stRow);
//            });
//
//            // Grand total for section
//            const gtRow = el('tr', 'bak-row-total');
//            let gtHtml = `<td class="col-code"></td><td>Total ${title}</td>`;
//            if (showDC) gtHtml += '<td></td><td></td>';
//            const tneg = total < 0 ? ' negative' : '';
//            gtHtml += `<td class="num${tneg}">${fmt(total)}</td>`;
//            if (showComp) {
//                const cn = compTotal < 0 ? ' negative' : '';
//                gtHtml += `<td class="num${cn}">${fmt(compTotal)}</td>`;
//            }
//            gtRow.innerHTML = gtHtml;
//            tbody.appendChild(gtRow);
//
//            // Spacer row
//            const sp = el('tr');
//            sp.innerHTML = `<td colspan="${secCols}" style="height:8px;background:var(--bak-bg)"></td>`;
//            tbody.appendChild(sp);
//        };
//
//        appendSection('Assets',      data.assets,      data.total_assets,      data.comp_total_assets || 0);
//        appendSection('Liabilities', data.liabilities, data.total_liabilities, data.comp_total_liabilities || 0);
//        appendSection('Equity',      data.equity,      data.total_equity,      data.comp_total_equity || 0);
//
//        // Liabilities + Equity
//        const leRow = el('tr', 'bak-row-le-total');
//        const leCols = 2 + (showDC ? 2 : 0) + 1 + (showComp ? 1 : 0);
//        let leHtml = `<td class="col-code"></td><td>LIABILITIES + EQUITY</td>`;
//        if (showDC) leHtml += '<td></td><td></td>';
//        leHtml += `<td class="num">${fmt(data.total_liabilities_equity)}</td>`;
//        if (showComp) leHtml += `<td class="num">${fmt(data.comp_total_liabilities_equity || 0)}</td>`;
//        leRow.innerHTML = leHtml;
//        tbody.appendChild(leRow);
//
//        table.appendChild(tbody);
//
//        // Click delegation for clickable amounts to drill down to journal items
//        table.addEventListener('click', (ev) => {
//            const target = ev.target.closest('.bak-clickable-amount');
//            if (target) {
//                const accId = target.dataset.accId;
//                if (accId === 'current_year_earnings') {
//                    // Do not drill down for the synthetic Current Year Earnings line
//                    return;
//                }
//                const type = target.dataset.type;
//                console.log("[Balance Sheet] Extracted dataset values:", { accId, type });
//                openJournalItems(accId, type);
//            }
//        });
//
//        wrap.appendChild(table);
//    }
//
//    // ── Open Journal Items Action ────────────────────────────────
//    function openJournalItems(accId, type) {
//        console.log("[Balance Sheet] openJournalItems called with:", { accId, type });
//        const domain = [['account_id', '=', parseInt(accId)]];
//        let dateFrom = state.dateFrom;
//        let dateTo = state.dateTo;
//
//        if (type === 'comp_balance') {
//            const compFromInp = document.getElementById('flt_comp_date_from');
//            const compToInp = document.getElementById('flt_comp_date_to');
//            dateFrom = compFromInp ? compFromInp.value : '';
//            dateTo = compToInp ? compToInp.value : '';
//        } else if (type === 'debit') {
//            domain.push(['debit', '>', 0]);
//        } else if (type === 'credit') {
//            domain.push(['credit', '>', 0]);
//        }
//
//        if (dateFrom) {
//            domain.push(['date', '>=', dateFrom]);
//        }
//        if (dateTo) {
//            domain.push(['date', '<=', dateTo]);
//        }
//        if (state.targetMove === 'posted') {
//            domain.push(['parent_state', '=', 'posted']);
//        }
//
//        if (state.analyticIds && state.analyticIds.length > 0) {
//            domain.push(['analytic_account_ids', 'in', state.analyticIds]);
//        }
//
//        const context = {
//            active_id: parseInt(accId),
//            active_ids: [parseInt(accId)],
//            search_default_posted: state.targetMove === 'posted' ? 1 : 0
//        };
//
//        if (state.analyticIds && state.analyticIds.length > 0) {
//            context['search_default_analytic_account_ids'] = state.analyticIds;
//        }
//
//        console.log("[Balance Sheet] Navigating to journal items with domain:", domain, "and context:", context);
//        const url = `/odoo/action-account.action_move_line_select?active_id=${accId}&active_ids=[${accId}]&domain=${encodeURIComponent(JSON.stringify(domain))}&context=${encodeURIComponent(JSON.stringify(context))}`;
//        console.log("[Balance Sheet] Generated redirection URL:", url);
//        window.open(url, '_blank');
//    }
//
//    // ── Loading / error states ───────────────────────────────────
//    function showLoading() {
//        const wrap = document.getElementById('bak_report_content');
//        wrap.innerHTML = `
//            <div class="bak-loading">
//                <div class="bak-spinner"></div>
//                <span>Loading report…</span>
//            </div>`;
//    }
//
//    function showError(msg) {
//        const wrap = document.getElementById('bak_report_content');
//        wrap.innerHTML = `
//            <div style="padding:40px;text-align:center;color:#c00;">
//                &#9888; ${msg}
//            </div>`;
//    }
//
//    // ── Download helpers ─────────────────────────────────────────
//    function downloadPDF() {
//        window.open('/bak/balance_sheet/pdf?wizard_id=' + state.wizardId, '_blank');
//    }
//
//    function downloadXLSX() {
//        window.location.href = '/bak/balance_sheet/xlsx?wizard_id=' + state.wizardId;
//    }
//
//    // ── Boot ─────────────────────────────────────────────────────
//    let initialized = false;
//    function boot() {
//        if (initialized) return;
//        initialized = true;
//        initControls();
//        loadAnalyticAccounts();
//        fetchReport();
//    }
//
//    document.addEventListener('DOMContentLoaded', boot);
//    if (document.readyState !== 'loading') {
//        boot();
//    }
//
//})();
/**
 * BAK Balance Sheet Inline Report – Client JS
 * Handles: filter application, data fetch from JSON endpoint,
 *          PDF/XLSX download, and mounts an interactive Owl component
 *          that renders the report table (incl. collapse/expand and the
 *          new "Split Horizontally" layout toggle).
 */
(function () {
    'use strict';

    // ── DOM helpers ────────────────────────────────────────────
    const $ = (sel, ctx) => (ctx || document).querySelector(sel);
    const $$ = (sel, ctx) => [...(ctx || document).querySelectorAll(sel)];
    const el = (tag, cls, html) => {
        const e = document.createElement(tag);
        if (cls) e.className = cls;
        if (html !== undefined) e.innerHTML = html;
        return e;
    };

    // ── State ──────────────────────────────────────────────────
    const app = document.getElementById('bak_bs_app');
    if (!app) return;

    const state = {
        wizardId:    app.dataset.wizardId,
        dateTo:      app.dataset.dateTo || '',
        dateFrom:    app.dataset.dateFrom || '',
        targetMove:  app.dataset.targetMove || 'posted',
        showDC:      app.dataset.displayDc === 'true',
        comparison:  false,
        compDateTo:  '',
        compDateFrom:'',
        analyticIds: [],
    };

    // =============================================================
    // Owl component: renders the report body (header, tables, totals)
    // =============================================================
    let ReportComponent = null;
    let reportRoot = null; // mounted Owl component instance

    function defineReportComponent() {
        if (!window.owl) {
            console.error('[Balance Sheet] Owl runtime (owl.js) was not found on the page.');
            return;
        }
        const { Component, useState, xml } = owl;

        class BalanceSheetReport extends Component {
            static template = xml`
                <div class="bak-report-inner">
                    <t t-if="state.error">
                        <div style="padding:40px;text-align:center;color:#c00;">
                            &#9888; <t t-esc="state.error"/>
                        </div>
                    </t>
                    <t t-elif="state.loading || !state.data">
                        <div class="bak-loading">
                            <div class="bak-spinner"></div>
                            <span>Loading report&#8230;</span>
                        </div>
                    </t>
                    <t t-else="">
                        <div class="bak-rpt-header">
                            <div class="bak-rpt-company"><t t-esc="state.data.company_name"/></div>
                            <div class="bak-rpt-period">
                                As of <strong><t t-esc="state.data.date_to"/></strong>
                                <t t-if="state.data.date_from"> &#8212; From <t t-esc="state.data.date_from"/></t>
                                &#160;|&#160;
                                <t t-esc="state.data.target_move === 'posted' ? 'Posted Entries' : 'All Entries'"/>
                            </div>
                        </div>

                        <div t-att-class="state.splitHorizontal ? 'bak-rpt-body-split' : 'bak-rpt-body-stack'">
                            <t t-foreach="this.sections" t-as="sec" t-key="sec.key">
                                <div t-att-class="'bak-sec-block sec-' + sec.key">
                                    <table class="bak-rpt-table">
                                        <thead>
                                            <tr>
                                                <th>Code</th>
                                                <th>Account</th>
                                                <t t-if="state.data.display_debit_credit">
                                                    <th class="num">Debit</th>
                                                    <th class="num">Credit</th>
                                                </t>
                                                <th class="num">Balance</th>
                                                <t t-if="state.data.enable_comparison">
                                                    <th class="num">As of <t t-esc="state.data.comparison_date_to || 'Prev'"/></th>
                                                </t>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr t-att-class="state.collapsed[sec.key] ? 'bak-row-section collapsed' : 'bak-row-section'"
                                                t-on-click="() => this.toggleSection(sec.key)">
                                                <td t-att-colspan="this.cols">
                                                    <span class="bak-toggle">&#9660;</span>
                                                    <t t-esc="sec.title.toUpperCase()"/>
                                                </td>
                                            </tr>
                                            <t t-if="!state.collapsed[sec.key]">
                                                <t t-foreach="sec.subsections" t-as="sub" t-key="sub.name">
                                                    <tr class="bak-row-subsection">
                                                        <td t-att-colspan="this.cols"><t t-esc="sub.name"/></td>
                                                    </tr>
                                                    <t t-foreach="sub.rows" t-as="row" t-key="sub.name + '_' + row.id">
                                                        <tr class="bak-row-account">
                                                            <td class="col-code"><t t-esc="row.code || ''"/></td>
                                                            <td><t t-esc="row.name"/></td>
                                                            <t t-if="state.data.display_debit_credit">
                                                                <td class="num">
                                                                    <span class="bak-clickable-amount"
                                                                          t-on-click="() => this.onAmountClick(row.id, 'debit')">
                                                                        <t t-esc="this.fmt(row.debit)"/>
                                                                    </span>
                                                                </td>
                                                                <td class="num">
                                                                    <span class="bak-clickable-amount"
                                                                          t-on-click="() => this.onAmountClick(row.id, 'credit')">
                                                                        <t t-esc="this.fmt(row.credit)"/>
                                                                    </span>
                                                                </td>
                                                            </t>
                                                            <td class="num" t-att-class="this.negClass(row.balance)">
                                                                <span class="bak-clickable-amount"
                                                                      t-on-click="() => this.onAmountClick(row.id, 'balance')">
                                                                    <t t-esc="this.fmt(row.balance)"/>
                                                                </span>
                                                            </td>
                                                            <t t-if="state.data.enable_comparison">
                                                                <td class="num" t-att-class="this.negClass(row.comp_balance)">
                                                                    <span class="bak-clickable-amount"
                                                                          t-on-click="() => this.onAmountClick(row.id, 'comp_balance')">
                                                                        <t t-esc="this.fmt(row.comp_balance)"/>
                                                                    </span>
                                                                </td>
                                                            </t>
                                                        </tr>
                                                    </t>
                                                    <tr class="bak-row-subtotal">
                                                        <td class="col-code"></td>
                                                        <td><t t-esc="'Total ' + sub.name"/></td>
                                                        <t t-if="state.data.display_debit_credit"><td></td><td></td></t>
                                                        <td class="num" t-att-class="this.negClass(sub.subtotal)">
                                                            <t t-esc="this.fmt(sub.subtotal)"/>
                                                        </td>
                                                        <t t-if="state.data.enable_comparison">
                                                            <td class="num" t-att-class="this.negClass(sub.comp_subtotal)">
                                                                <t t-esc="this.fmt(sub.comp_subtotal)"/>
                                                            </td>
                                                        </t>
                                                    </tr>
                                                </t>
                                                <tr class="bak-row-total">
                                                    <td class="col-code"></td>
                                                    <td><t t-esc="'Total ' + sec.title"/></td>
                                                    <t t-if="state.data.display_debit_credit"><td></td><td></td></t>
                                                    <td class="num" t-att-class="this.negClass(sec.total)">
                                                        <t t-esc="this.fmt(sec.total)"/>
                                                    </td>
                                                    <t t-if="state.data.enable_comparison">
                                                        <td class="num" t-att-class="this.negClass(sec.compTotal)">
                                                            <t t-esc="this.fmt(sec.compTotal)"/>
                                                        </td>
                                                    </t>
                                                </tr>
                                            </t>
                                        </tbody>
                                    </table>
                                </div>
                            </t>

                            <div class="bak-sec-block sec-le-total">
                                <table class="bak-rpt-table">
                                    <tbody>
                                        <tr class="bak-row-le-total">
                                            <td class="col-code"></td>
                                            <td>LIABILITIES + EQUITY</td>
                                            <t t-if="state.data.display_debit_credit"><td></td><td></td></t>
                                            <td class="num"><t t-esc="this.fmt(state.data.total_liabilities_equity)"/></td>
                                            <t t-if="state.data.enable_comparison">
                                                <td class="num">
                                                    <t t-esc="this.fmt(state.data.comp_total_liabilities_equity || 0)"/>
                                                </td>
                                            </t>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </t>
                </div>
            `;

            setup() {
                this.state = useState({
                    data: null,
                    loading: true,
                    error: null,
                    collapsed: {}, // { assets: bool, liabilities: bool, equity: bool }
                    splitHorizontal: false,
                });
            }

            // ── computed helpers ─────────────────────────────
            get sections() {
                const d = this.state.data;
                if (!d) return [];
                return [
                    { key: 'assets', title: 'Assets', subsections: d.assets || [],
                      total: d.total_assets || 0, compTotal: d.comp_total_assets || 0 },
                    { key: 'liabilities', title: 'Liabilities', subsections: d.liabilities || [],
                      total: d.total_liabilities || 0, compTotal: d.comp_total_liabilities || 0 },
                    { key: 'equity', title: 'Equity', subsections: d.equity || [],
                      total: d.total_equity || 0, compTotal: d.comp_total_equity || 0 },
                ];
            }

            get cols() {
                const d = this.state.data;
                if (!d) return 3;
                return 2 + (d.display_debit_credit ? 2 : 0) + 1 + (d.enable_comparison ? 1 : 0);
            }

            fmt(n) {
                if (n === null || n === undefined) return '';
                const sym = (this.state.data && this.state.data.currency_symbol) || '';
                const abs = Math.abs(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                return (n < 0 ? '-' : '') + sym + ' ' + abs;
            }

            negClass(v) {
                return (v || 0) < 0 ? 'negative' : '';
            }

            // ── interactions ─────────────────────────────────
            toggleSection(key) {
                this.state.collapsed[key] = !this.state.collapsed[key];
            }

            onAmountClick(accId, type) {
                if (accId === 'current_year_earnings') return;
                if (this.props.onAmountClick) this.props.onAmountClick(accId, type);
            }

            // ── public API used by the vanilla-JS controller code below ──
            setLoading() {
                this.state.loading = true;
                this.state.error = null;
            }
            setData(data) {
                this.state.data = data;
                this.state.loading = false;
                this.state.error = null;
                this.state.collapsed = {};
            }
            setError(msg) {
                this.state.error = msg;
                this.state.loading = false;
            }
            toggleSplitHorizontal() {
                this.state.splitHorizontal = !this.state.splitHorizontal;
                return this.state.splitHorizontal;
            }
        }

        ReportComponent = BalanceSheetReport;
    }

    async function mountReportComponent() {
        const target = document.getElementById('bak_report_content');

        if (!window.owl) {
            target.innerHTML = `
                <div style="padding:40px;text-align:center;color:#c00;">
                    &#9888; Owl runtime failed to load (owl.js).<br/>
                    <span style="font-size:11px;color:#888;">
                        Check the Network tab for a 404 on /web/static/lib/owl/owl.js
                        and adjust the URL in balance_sheet_controller.py if needed.
                    </span>
                </div>`;
            console.error('[Balance Sheet] window.owl is undefined — owl.js did not load.');
            return;
        }

        defineReportComponent();
        if (!ReportComponent) {
            target.innerHTML = `
                <div style="padding:40px;text-align:center;color:#c00;">
                    &#9888; Failed to build the report component. See browser console for details.
                </div>`;
            return;
        }

        target.innerHTML = '';
        const mountProps = { onAmountClick: openJournalItems };
        try {
            if (typeof owl.mount === 'function') {
                // Most Odoo 17+ owl.js builds expose a top-level mount() helper.
                reportRoot = await owl.mount(ReportComponent, target, { props: mountProps });
            } else if (owl.App) {
                // Fallback for builds that only expose the App class.
                const owlApp = new owl.App(ReportComponent, { props: mountProps });
                reportRoot = await owlApp.mount(target);
            } else {
                throw new Error('Neither owl.mount() nor owl.App was found on the owl global.');
            }
        } catch (err) {
            console.error('[Balance Sheet] Owl mount failed:', err);
            target.innerHTML = `
                <div style="padding:40px;text-align:center;color:#c00;">
                    &#9888; Could not render the report (template error).<br/>
                    <span style="font-size:11px;color:#888;">${(err && err.message) || err}</span><br/>
                    <span style="font-size:11px;color:#888;">Open the browser console for the full stack trace.</span>
                </div>`;
            reportRoot = null;
        }
    }

    // =============================================================
    // Vanilla JS: filter bar, downloads, analytic dropdown
    // (kept simple/framework-free — only the report body is Owl-driven)
    // =============================================================

    function initControls() {
        $('#flt_date_to').value  = state.dateTo;
        $('#flt_date_from').value = state.dateFrom;
        $('#chk_dc').checked     = state.showDC;
        $('#sel_moves').value    = state.targetMove;

        $('#btn_apply').addEventListener('click', applyFilters);
        $('#btn_pdf').addEventListener('click', downloadPDF);
        $('#btn_xlsx').addEventListener('click', downloadXLSX);
        $('#btn_comparison').addEventListener('click', toggleComparison);
        $('#btn_split').addEventListener('click', toggleSplitHorizontal);

        // Enter key on date inputs
        ['flt_date_to','flt_date_from','flt_comp_date_to','flt_comp_date_from'].forEach(id => {
            const inp = document.getElementById(id);
            if (inp) inp.addEventListener('keydown', e => { if (e.key === 'Enter') applyFilters(); });
        });

        // Dropdown toggle listener
        const dropdownBtn = $('#analytic_dropdown_btn');
        const dropdownContent = $('#analytic_dropdown_content');
        if (dropdownBtn && dropdownContent) {
            dropdownBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                const show = dropdownContent.style.display === 'none';
                dropdownContent.style.display = show ? 'block' : 'none';
            });
            document.addEventListener('click', (e) => {
                if (!dropdownContent.contains(e.target) && e.target !== dropdownBtn) {
                    dropdownContent.style.display = 'none';
                }
            });
        }
    }

    function toggleComparison() {
        state.comparison = !state.comparison;
        $('#btn_comparison').classList.toggle('active', state.comparison);
        $('#grp_comparison').style.display      = state.comparison ? '' : 'none';
        $('#grp_comparison_from').style.display = state.comparison ? '' : 'none';
    }

    // ── Split Horizontally toggle ────────────────────────────────
    function toggleSplitHorizontal() {
        if (!reportRoot) return;
        const next = reportRoot.toggleSplitHorizontal();
        $('#btn_split').classList.toggle('active', next);
        $('#bak_report_content').classList.toggle('bak-wide', next);
    }

    // ── Apply filters → fetch data ──────────────────────────────
    function applyFilters() {
        state.dateTo      = $('#flt_date_to').value;
        state.dateFrom    = $('#flt_date_from').value;
        state.showDC      = $('#chk_dc').checked;
        state.targetMove  = $('#sel_moves').value;
        state.compDateTo  = $('#flt_comp_date_to') ? $('#flt_comp_date_to').value : '';
        state.compDateFrom= $('#flt_comp_date_from') ? $('#flt_comp_date_from').value : '';
        fetchReport();
    }

    // ── JSON RPC call ───────────────────────────────────────────
    async function fetchReport() {
        showLoading();
        try {
            const body = {
                jsonrpc: '2.0',
                method: 'call',
                id: 1,
                params: {
                    wizard_id:          state.wizardId,
                    date_to:            state.dateTo || null,
                    date_from:          state.dateFrom || null,
                    target_move:        state.targetMove,
                    display_debit_credit: state.showDC,
                    enable_comparison:  state.comparison,
                    comparison_date_to: state.compDateTo || null,
                    comparison_date_from: state.compDateFrom || null,
                    analytic_ids:       state.analyticIds || [],
                },
            };
            const res  = await fetch('/bak/balance_sheet/data', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify(body),
            });
            const json = await res.json();
            if (json.error) {
                showError(json.error.data?.message || 'Server error');
                return;
            }
            renderReport(json.result);
        } catch (err) {
            showError('Network error: ' + err.message);
        }
    }

    // ── Fetch and initialize Analytic Accounts ─────────────────
    async function loadAnalyticAccounts() {
        try {
            const body = {
                jsonrpc: '2.0',
                method: 'call',
                id: 2,
                params: {},
            };
            const res = await fetch('/bak/balance_sheet/analytic_accounts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            const json = await res.json();
            if (json.result) {
                renderAnalyticDropdown(json.result);
            }
        } catch (e) {
            console.error("Failed to load analytic accounts:", e);
        }
    }

    function renderAnalyticDropdown(accounts) {
        const list = $('#analytic_items_list');
        if (!list) return;
        list.innerHTML = '';

        accounts.forEach(acc => {
            const item = el('label', 'bak-dropdown-item');
            item.innerHTML = `<input type="checkbox" data-id="${acc.id}" value="${acc.name}"/> <span>${acc.name}</span>`;
            list.appendChild(item);
        });

        const btn = $('#analytic_dropdown_btn');
        const checkboxes = $$('#analytic_items_list input[type="checkbox"]');

        checkboxes.forEach(chk => {
            chk.addEventListener('change', () => {
                const selected = checkboxes.filter(c => c.checked);
                state.analyticIds = selected.map(c => parseInt(c.dataset.id));
                if (selected.length === 0) {
                    btn.innerText = 'Select Analytic Accounts...';
                } else if (selected.length === 1) {
                    btn.innerText = selected[0].value;
                } else {
                    btn.innerText = `${selected.length} Selected`;
                }
            });
        });

        const searchInput = $('#analytic_search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                const q = e.target.value.toLowerCase();
                const items = $$('.bak-dropdown-item', list);
                items.forEach(item => {
                    const text = item.querySelector('span').innerText.toLowerCase();
                    item.style.display = text.includes(q) ? '' : 'none';
                });
            });
        }
    }

    // ── Render (delegates to the Owl component) ──────────────────
    function renderReport(data) {
        if (!reportRoot) return;
        reportRoot.setData(data);
    }

    function showLoading() {
        if (!reportRoot) return;
        reportRoot.setLoading();
    }

    function showError(msg) {
        if (!reportRoot) return;
        reportRoot.setError(msg);
    }

    // ── Open Journal Items Action ────────────────────────────────
    function openJournalItems(accId, type) {
        const domain = [['account_id', '=', parseInt(accId)]];
        let dateFrom = state.dateFrom;
        let dateTo = state.dateTo;

        if (type === 'comp_balance') {
            const compFromInp = document.getElementById('flt_comp_date_from');
            const compToInp = document.getElementById('flt_comp_date_to');
            dateFrom = compFromInp ? compFromInp.value : '';
            dateTo = compToInp ? compToInp.value : '';
        } else if (type === 'debit') {
            domain.push(['debit', '>', 0]);
        } else if (type === 'credit') {
            domain.push(['credit', '>', 0]);
        }

        if (dateFrom) {
            domain.push(['date', '>=', dateFrom]);
        }
        if (dateTo) {
            domain.push(['date', '<=', dateTo]);
        }
        if (state.targetMove === 'posted') {
            domain.push(['parent_state', '=', 'posted']);
        }

        if (state.analyticIds && state.analyticIds.length > 0) {
            domain.push(['analytic_account_ids', 'in', state.analyticIds]);
        }

        const context = {
            active_id: parseInt(accId),
            active_ids: [parseInt(accId)],
            search_default_posted: state.targetMove === 'posted' ? 1 : 0
        };

        if (state.analyticIds && state.analyticIds.length > 0) {
            context['search_default_analytic_account_ids'] = state.analyticIds;
        }

        const url = `/odoo/action-account.action_move_line_select?active_id=${accId}&active_ids=[${accId}]&domain=${encodeURIComponent(JSON.stringify(domain))}&context=${encodeURIComponent(JSON.stringify(context))}`;
        window.open(url, '_blank');
    }

    // ── Download helpers ─────────────────────────────────────────
    function downloadPDF() {
        window.open('/bak/balance_sheet/pdf?wizard_id=' + state.wizardId, '_blank');
    }

    function downloadXLSX() {
        window.location.href = '/bak/balance_sheet/xlsx?wizard_id=' + state.wizardId;
    }

    // ── Boot ─────────────────────────────────────────────────────
    let initialized = false;
    async function boot() {
        if (initialized) return;
        initialized = true;
        await mountReportComponent();
        initControls();
        loadAnalyticAccounts();
        fetchReport();
    }

    document.addEventListener('DOMContentLoaded', boot);
    if (document.readyState !== 'loading') {
        boot();
    }

})();