/**
 * BAK Balance Sheet Inline Report – Client JS
 * Handles: filter application, data fetch from JSON endpoint,
 *          dynamic HTML rendering, PDF/XLSX download, expand/collapse.
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
    };

    // ── Wire up filter controls ─────────────────────────────────
    function initControls() {
        $('#flt_date_to').value  = state.dateTo;
        $('#flt_date_from').value = state.dateFrom;
        $('#chk_dc').checked     = state.showDC;
        $('#sel_moves').value    = state.targetMove;

        $('#btn_apply').addEventListener('click', applyFilters);
        $('#btn_pdf').addEventListener('click', downloadPDF);
        $('#btn_xlsx').addEventListener('click', downloadXLSX);
        $('#btn_comparison').addEventListener('click', toggleComparison);

        // Enter key on date inputs
        ['flt_date_to','flt_date_from','flt_comp_date_to','flt_comp_date_from'].forEach(id => {
            const inp = document.getElementById(id);
            if (inp) inp.addEventListener('keydown', e => { if (e.key === 'Enter') applyFilters(); });
        });
    }

    function toggleComparison() {
        state.comparison = !state.comparison;
        $('#btn_comparison').classList.toggle('active', state.comparison);
        $('#grp_comparison').style.display      = state.comparison ? '' : 'none';
        $('#grp_comparison_from').style.display = state.comparison ? '' : 'none';
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

    // ── Render ──────────────────────────────────────────────────
    function renderReport(data) {
        const wrap = document.getElementById('bak_report_content');
        wrap.innerHTML = '';

        const showDC   = data.display_debit_credit;
        const showComp = data.enable_comparison;
        const sym      = data.currency_symbol || '';

        // Header
        const hdr = el('div', 'bak-rpt-header');
        hdr.innerHTML = `
            <div class="bak-rpt-company">${data.company_name}</div>
            <div class="bak-rpt-period">
                As of <strong>${data.date_to}</strong>
                ${data.date_from ? ' &mdash; From ' + data.date_from : ''}
                &nbsp;|&nbsp;
                ${data.target_move === 'posted' ? 'Posted Entries' : 'All Entries'}
            </div>`;
        wrap.appendChild(hdr);

        // Table
        const table = el('table', 'bak-rpt-table');

        // THEAD
        const thead = el('thead');
        let headHtml = '<tr><th>Code</th><th>Account</th>';
        if (showDC)   headHtml += '<th class="num">Debit</th><th class="num">Credit</th>';
        headHtml += '<th class="num">Balance</th>';
        if (showComp) headHtml += `<th class="num">As of ${data.comparison_date_to || 'Prev'}</th>`;
        headHtml += '</tr>';
        thead.innerHTML = headHtml;
        table.appendChild(thead);

        const tbody = el('tbody');

        // Helper: format number
        const fmt = (n) => {
            if (n === null || n === undefined) return '';
            const abs = Math.abs(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
            return (n < 0 ? '-' : '') + sym + ' ' + abs;
        };

        const appendSection = (title, subsections, total, compTotal) => {
            // Section header row
            const secRow = el('tr', 'bak-row-section');
            const secCols = 2 + (showDC ? 2 : 0) + 1 + (showComp ? 1 : 0);
            secRow.innerHTML = `
                <td colspan="${secCols}">
                    <span class="bak-toggle">&#9660;</span>
                    ${title.toUpperCase()}
                </td>`;
            secRow.addEventListener('click', () => {
                const collapsed = secRow.classList.toggle('collapsed');
                // toggle all child rows
                let sib = secRow.nextElementSibling;
                while (sib && !sib.classList.contains('bak-row-section') &&
                       !sib.classList.contains('bak-row-le-total')) {
                    sib.style.display = collapsed ? 'none' : '';
                    sib = sib.nextElementSibling;
                }
            });
            tbody.appendChild(secRow);

            subsections.forEach(sub => {
                // Sub-header
                const subRow = el('tr', 'bak-row-subsection');
                subRow.innerHTML = `<td colspan="${secCols}">${sub.name}</td>`;
                tbody.appendChild(subRow);

                // Account rows
                (sub.rows || []).forEach(row => {
                    const accRow = el('tr', 'bak-row-account');
                    const negClass = row.balance < 0 ? ' negative' : '';
                    let html = `
                        <td class="col-code">${row.code || ''}</td>
                        <td>${row.name}</td>`;
                    if (showDC) {
                        html += `
                        <td class="num">${fmt(row.debit)}</td>
                        <td class="num">${fmt(row.credit)}</td>`;
                    }
                    html += `<td class="num${negClass}">${fmt(row.balance)}</td>`;
                    if (showComp) {
                        const cn = row.comp_balance < 0 ? ' negative' : '';
                        html += `<td class="num${cn}">${fmt(row.comp_balance)}</td>`;
                    }
                    accRow.innerHTML = html;
                    tbody.appendChild(accRow);
                });

                // Subtotal row
                const stRow = el('tr', 'bak-row-subtotal');
                let stHtml = `<td class="col-code"></td><td>Total ${sub.name}</td>`;
                if (showDC) stHtml += '<td></td><td></td>';
                const sneg = sub.subtotal < 0 ? ' negative' : '';
                stHtml += `<td class="num${sneg}">${fmt(sub.subtotal)}</td>`;
                if (showComp) {
                    const cn = sub.comp_subtotal < 0 ? ' negative' : '';
                    stHtml += `<td class="num${cn}">${fmt(sub.comp_subtotal)}</td>`;
                }
                stRow.innerHTML = stHtml;
                tbody.appendChild(stRow);
            });

            // Grand total for section
            const gtRow = el('tr', 'bak-row-total');
            let gtHtml = `<td class="col-code"></td><td>Total ${title}</td>`;
            if (showDC) gtHtml += '<td></td><td></td>';
            const tneg = total < 0 ? ' negative' : '';
            gtHtml += `<td class="num${tneg}">${fmt(total)}</td>`;
            if (showComp) {
                const cn = compTotal < 0 ? ' negative' : '';
                gtHtml += `<td class="num${cn}">${fmt(compTotal)}</td>`;
            }
            gtRow.innerHTML = gtHtml;
            tbody.appendChild(gtRow);

            // Spacer row
            const sp = el('tr');
            sp.innerHTML = `<td colspan="${secCols}" style="height:8px;background:var(--bak-bg)"></td>`;
            tbody.appendChild(sp);
        };

        appendSection('Assets',      data.assets,      data.total_assets,      data.comp_total_assets || 0);
        appendSection('Liabilities', data.liabilities, data.total_liabilities, data.comp_total_liabilities || 0);
        appendSection('Equity',      data.equity,      data.total_equity,      data.comp_total_equity || 0);

        // Liabilities + Equity
        const leRow = el('tr', 'bak-row-le-total');
        const leCols = 2 + (showDC ? 2 : 0) + 1 + (showComp ? 1 : 0);
        let leHtml = `<td class="col-code"></td><td>LIABILITIES + EQUITY</td>`;
        if (showDC) leHtml += '<td></td><td></td>';
        leHtml += `<td class="num">${fmt(data.total_liabilities_equity)}</td>`;
        if (showComp) leHtml += `<td class="num">${fmt(data.comp_total_liabilities_equity || 0)}</td>`;
        leRow.innerHTML = leHtml;
        tbody.appendChild(leRow);

        table.appendChild(tbody);
        wrap.appendChild(table);
    }

    // ── Loading / error states ───────────────────────────────────
    function showLoading() {
        const wrap = document.getElementById('bak_report_content');
        wrap.innerHTML = `
            <div class="bak-loading">
                <div class="bak-spinner"></div>
                <span>Loading report…</span>
            </div>`;
    }

    function showError(msg) {
        const wrap = document.getElementById('bak_report_content');
        wrap.innerHTML = `
            <div style="padding:40px;text-align:center;color:#c00;">
                &#9888; ${msg}
            </div>`;
    }

    // ── Download helpers ─────────────────────────────────────────
    function downloadPDF() {
        window.open('/bak/balance_sheet/pdf?wizard_id=' + state.wizardId, '_blank');
    }

    function downloadXLSX() {
        window.location.href = '/bak/balance_sheet/xlsx?wizard_id=' + state.wizardId;
    }

    // ── Boot ─────────────────────────────────────────────────────
    document.addEventListener('DOMContentLoaded', () => {
        initControls();
        fetchReport();
    });

    // Also fire immediately if DOM already loaded
    if (document.readyState !== 'loading') {
        initControls();
        fetchReport();
    }

})();
