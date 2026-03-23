/**
 * BAK Profit & Loss Inline Report – Client JS
 * Handles: filter application, data fetch, dynamic HTML rendering,
 *          PDF/XLSX download, expand/collapse sections.
 */
(function () {
    'use strict';

    // ── DOM helpers ────────────────────────────────────────────
    const $  = (sel, ctx) => (ctx || document).querySelector(sel);
    const $$ = (sel, ctx) => [...(ctx || document).querySelectorAll(sel)];
    const el = (tag, cls, html) => {
        const e = document.createElement(tag);
        if (cls) e.className = cls;
        if (html !== undefined) e.innerHTML = html;
        return e;
    };

    // ── Boot ───────────────────────────────────────────────────
    const app = document.getElementById('bak_pl_app');
    if (!app) return;

    const state = {
        wizardId:     app.dataset.wizardId,
        dateFrom:     app.dataset.dateFrom  || '',
        dateTo:       app.dataset.dateTo    || '',
        targetMove:   app.dataset.targetMove || 'posted',
        showDC:       app.dataset.displayDc === 'true',
        comparison:   false,
        compDateFrom: '',
        compDateTo:   '',
    };

    // ── Wire controls ──────────────────────────────────────────
    function initControls() {
        $('#flt_date_from').value = state.dateFrom;
        $('#flt_date_to').value   = state.dateTo;
        $('#chk_dc').checked      = state.showDC;
        $('#sel_moves').value     = state.targetMove;

        $('#btn_apply').addEventListener('click', applyFilters);
        $('#btn_pdf').addEventListener('click', downloadPDF);
        $('#btn_xlsx').addEventListener('click', downloadXLSX);
        $('#btn_comparison').addEventListener('click', toggleComparison);

        ['flt_date_from','flt_date_to','flt_comp_date_from','flt_comp_date_to'].forEach(id => {
            const inp = document.getElementById(id);
            if (inp) inp.addEventListener('keydown', e => { if (e.key === 'Enter') applyFilters(); });
        });
    }

    function toggleComparison() {
        state.comparison = !state.comparison;
        $('#btn_comparison').classList.toggle('active', state.comparison);
        $('#grp_comparison').style.display    = state.comparison ? '' : 'none';
        $('#grp_comparison_to').style.display = state.comparison ? '' : 'none';
    }

    // ── Apply & fetch ──────────────────────────────────────────
    function applyFilters() {
        state.dateFrom     = $('#flt_date_from').value;
        state.dateTo       = $('#flt_date_to').value;
        state.showDC       = $('#chk_dc').checked;
        state.targetMove   = $('#sel_moves').value;
        state.compDateFrom = $('#flt_comp_date_from') ? $('#flt_comp_date_from').value : '';
        state.compDateTo   = $('#flt_comp_date_to')   ? $('#flt_comp_date_to').value   : '';
        fetchReport();
    }

    async function fetchReport() {
        showLoading();
        try {
            const body = {
                jsonrpc: '2.0', method: 'call', id: 1,
                params: {
                    wizard_id:             state.wizardId,
                    date_from:             state.dateFrom  || null,
                    date_to:               state.dateTo    || null,
                    target_move:           state.targetMove,
                    display_debit_credit:  state.showDC,
                    enable_comparison:     state.comparison,
                    comparison_date_from:  state.compDateFrom || null,
                    comparison_date_to:    state.compDateTo   || null,
                },
            };
            const res  = await fetch('/bak/profit_loss/data', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
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

    // ── Render ─────────────────────────────────────────────────
    function renderReport(data) {
        const wrap = document.getElementById('bak_report_content');
        wrap.innerHTML = '';

        const showDC   = data.display_debit_credit;
        const showComp = data.enable_comparison;
        const sym      = data.currency_symbol || '';

        // ── Format number ──────────────────────────────────────
        const fmt = (n) => {
            if (n === null || n === undefined) return '';
            const abs = Math.abs(n).toLocaleString('en-IN', {
                minimumFractionDigits: 2, maximumFractionDigits: 2
            });
            return (n < 0 ? '-' : '') + sym + ' ' + abs;
        };

        // ── Header ─────────────────────────────────────────────
        const period = data.date_from
            ? `From <strong>${data.date_from}</strong> to <strong>${data.date_to}</strong>`
            : `As of <strong>${data.date_to}</strong>`;

        const hdr = el('div', 'bak-rpt-header');
        hdr.innerHTML = `
            <div class="bak-rpt-company">${data.company_name}</div>
            <div class="bak-rpt-period">
                ${period} &nbsp;|&nbsp;
                ${data.target_move === 'posted' ? 'Posted Entries' : 'All Entries'}
            </div>`;
        wrap.appendChild(hdr);

        // ── Table ──────────────────────────────────────────────
        const table = el('table', 'bak-rpt-table');
        const thead = el('thead');
        const ncols = 2 + (showDC ? 2 : 0) + 1 + (showComp ? 1 : 0);
        let headHtml = '<tr><th>Code</th><th>Account</th>';
        if (showDC) headHtml += '<th class="num">Debit</th><th class="num">Credit</th>';
        headHtml += '<th class="num">Amount</th>';
        if (showComp) headHtml += `<th class="num">Comp (${data.comparison_date_to || 'Prev'})</th>`;
        headHtml += '</tr>';
        thead.innerHTML = headHtml;
        table.appendChild(thead);

        const tbody = el('tbody');

        // ── Helper: append a collapsible section ───────────────
        const appendSection = (title, subsections, total, compTotal) => {
            const secRow = el('tr', 'bak-row-section');
            secRow.innerHTML = `<td colspan="${ncols}">
                <span class="bak-toggle">&#9660;</span>${title.toUpperCase()}
            </td>`;
            secRow.addEventListener('click', () => {
                const collapsed = secRow.classList.toggle('collapsed');
                let sib = secRow.nextElementSibling;
                while (sib && !sib.classList.contains('bak-row-section') &&
                       !sib.classList.contains('bak-row-gross-profit') &&
                       !sib.classList.contains('bak-row-net-profit')) {
                    sib.style.display = collapsed ? 'none' : '';
                    sib = sib.nextElementSibling;
                }
            });
            tbody.appendChild(secRow);

            subsections.forEach(sub => {
                const subRow = el('tr', 'bak-row-subsection');
                subRow.innerHTML = `<td colspan="${ncols}">${sub.name}</td>`;
                tbody.appendChild(subRow);

                (sub.rows || []).forEach(row => {
                    const accRow = el('tr', 'bak-row-account');
                    const negCls = row.balance < 0 ? ' negative' : '';
                    let html = `
                        <td class="col-code">${row.code || ''}</td>
                        <td>${row.name}</td>`;
                    if (showDC) {
                        html += `<td class="num">${fmt(row.debit)}</td>
                                 <td class="num">${fmt(row.credit)}</td>`;
                    }
                    html += `<td class="num${negCls}">${fmt(row.balance)}</td>`;
                    if (showComp) {
                        const cn = row.comp_balance < 0 ? ' negative' : '';
                        html += `<td class="num${cn}">${fmt(row.comp_balance)}</td>`;
                    }
                    accRow.innerHTML = html;
                    tbody.appendChild(accRow);
                });

                // Subtotal
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

            // Section total
            const totRow = el('tr', 'bak-row-total');
            let totHtml = `<td class="col-code"></td><td>Total ${title}</td>`;
            if (showDC) totHtml += '<td></td><td></td>';
            const tneg = total < 0 ? ' negative' : '';
            totHtml += `<td class="num${tneg}">${fmt(total)}</td>`;
            if (showComp) {
                const cn = compTotal < 0 ? ' negative' : '';
                totHtml += `<td class="num${cn}">${fmt(compTotal)}</td>`;
            }
            totRow.innerHTML = totHtml;
            tbody.appendChild(totRow);

            // Spacer
            const sp = el('tr', 'bak-row-spacer');
            sp.innerHTML = `<td colspan="${ncols}" style="height:8px"></td>`;
            tbody.appendChild(sp);
        };

        // ── Helper: summary row (Gross / Net Profit) ───────────
        const appendSummaryRow = (title, value, compValue, rowCls) => {
            const row = el('tr', rowCls);
            let html = `<td class="col-code"></td><td>${title}</td>`;
            if (showDC) html += '<td></td><td></td>';
            const negCls = value < 0 ? ' negative' : '';
            html += `<td class="num${negCls}">${fmt(value)}</td>`;
            if (showComp) {
                const cn = compValue < 0 ? ' negative' : '';
                html += `<td class="num${cn}">${fmt(compValue)}</td>`;
            }
            row.innerHTML = html;
            tbody.appendChild(row);

            const sp = el('tr', 'bak-row-spacer');
            sp.innerHTML = `<td colspan="${ncols}" style="height:10px"></td>`;
            tbody.appendChild(sp);
        };

        // ── Build report ───────────────────────────────────────
        appendSection('Revenue',
            data.revenue,
            data.total_revenue,
            data.comp_total_revenue || 0);

        appendSection('Cost of Revenue',
            data.cogs,
            data.total_cogs,
            data.comp_total_cogs || 0);

        appendSummaryRow(
            '&#9650; GROSS PROFIT',
            data.gross_profit,
            data.comp_gross_profit || 0,
            'bak-row-gross-profit');

        appendSection('Operating Expenses',
            data.opex,
            data.total_opex,
            data.comp_total_opex || 0);

        appendSummaryRow(
            '&#9733; NET PROFIT',
            data.net_profit,
            data.comp_net_profit || 0,
            'bak-row-net-profit');

        table.appendChild(tbody);
        wrap.appendChild(table);
    }

    // ── Loading / error ─────────────────────────────────────────
    function showLoading() {
        document.getElementById('bak_report_content').innerHTML = `
            <div class="bak-loading">
                <div class="bak-spinner"></div>
                <span>Loading report…</span>
            </div>`;
    }

    function showError(msg) {
        document.getElementById('bak_report_content').innerHTML = `
            <div style="padding:40px;text-align:center;color:#c00;">
                &#9888; ${msg}
            </div>`;
    }

    // ── Downloads ───────────────────────────────────────────────
    function downloadPDF() {
        window.open('/bak/profit_loss/pdf?wizard_id=' + state.wizardId, '_blank');
    }
    function downloadXLSX() {
        window.location.href = '/bak/profit_loss/xlsx?wizard_id=' + state.wizardId;
    }

    // ── Init ────────────────────────────────────────────────────
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => { initControls(); fetchReport(); });
    } else {
        initControls();
        fetchReport();
    }

})();
