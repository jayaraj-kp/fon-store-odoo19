# -*- coding: utf-8 -*-
import json
import io
from odoo import http, fields
from odoo.http import request, content_disposition, Response
import logging

_logger = logging.getLogger(__name__)


class BalanceSheetController(http.Controller):

    # ------------------------------------------------------------------
    # Main HTML report page
    # ------------------------------------------------------------------
    @http.route('/bak/balance_sheet', type='http', auth='user', website=False)
    def balance_sheet_main(self, wizard_id=None, **kwargs):
        """Render the main balance sheet inline report page."""
        env = request.env
        if wizard_id:
            wizard = env['bak.balance.sheet.report'].browse(int(wizard_id))
            if not wizard.exists():
                wizard = env['bak.balance.sheet.report'].create({})
        else:
            wizard = env['bak.balance.sheet.report'].create({})

        # Build HTML directly — avoids any web.layout / website dependency
        date_to = str(wizard.date_to or fields.Date.today())
        date_from = str(wizard.date_from) if wizard.date_from else ''

        html = self._render_page(wizard.id, date_to, date_from,
                                 wizard.target_move,
                                 wizard.display_debit_credit)
        return Response(html, content_type='text/html;charset=utf-8', status=200)

    def _render_page(self, wizard_id, date_to, date_from,
                     target_move, display_debit_credit):
        """Return the full HTML page as a string."""
        css_url = '/bak_balance_sheet_report/static/src/css/balance_sheet.css'
        js_url  = '/bak_balance_sheet_report/static/src/js/balance_sheet_action.js'
        dc_val  = 'true' if display_debit_credit else 'false'

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <title>Balance Sheet</title>
    <link rel="stylesheet" href="{css_url}"/>
    <style>
        /* Odoo backend already loaded — just reset body margin */
        body {{ margin: 0; padding: 0; background: #F5F5F8; }}
    </style>
</head>
<body>
<div id="bak_bs_app"
     data-wizard-id="{wizard_id}"
     data-date-to="{date_to}"
     data-date-from="{date_from}"
     data-target-move="{target_move}"
     data-display-dc="{dc_val}">

    <!-- ── TOP BAR ──────────────────────────────────────────── -->
    <div class="bak-bs-topbar">
        <div class="bak-bs-topbar-left">
            <a href="/odoo/accounting" class="bak-bs-back">&#8592; Accounting</a>
            <span class="bak-bs-title">Balance Sheet</span>
        </div>
        <div class="bak-bs-topbar-right">
            <button class="bak-btn bak-btn-outline" id="btn_pdf">&#128438; PDF</button>
            <button class="bak-btn bak-btn-outline" id="btn_xlsx">&#128202; XLSX</button>
            <button class="bak-btn bak-btn-outline" id="btn_comparison">&#8646; Comparison</button>
            <select class="bak-select" id="sel_moves">
                <option value="posted">Posted Entries</option>
                <option value="all">All Entries</option>
            </select>
        </div>
    </div>

    <!-- ── FILTER BAR ───────────────────────────────────────── -->
    <div class="bak-bs-filterbar">
        <div class="bak-filter-group">
            <label>As of Date</label>
            <input type="date" id="flt_date_to" class="bak-input"/>
        </div>
        <div class="bak-filter-group">
            <label>From Date</label>
            <input type="date" id="flt_date_from" class="bak-input"/>
        </div>
        <div class="bak-filter-group">
            <label class="bak-check-label">
                <input type="checkbox" id="chk_dc"/> Show Debit/Credit
            </label>
        </div>
        <div class="bak-filter-group" id="grp_comparison" style="display:none">
            <label>Compare As of</label>
            <input type="date" id="flt_comp_date_to" class="bak-input"/>
        </div>
        <div class="bak-filter-group" id="grp_comparison_from" style="display:none">
            <label>Compare From</label>
            <input type="date" id="flt_comp_date_from" class="bak-input"/>
        </div>
        <div class="bak-filter-group">
            <button class="bak-btn bak-btn-primary" id="btn_apply">&#8635; Apply</button>
        </div>
    </div>

    <!-- ── REPORT CONTENT ───────────────────────────────────── -->
    <div class="bak-bs-body">
        <div id="bak_report_content" class="bak-report-wrap">
            <div class="bak-loading">
                <div class="bak-spinner"></div>
                <span>Loading report&hellip;</span>
            </div>
        </div>
    </div>

</div>
<script src="{js_url}"></script>
</body>
</html>"""

    # ------------------------------------------------------------------
    # JSON endpoint – fetch report data
    # ------------------------------------------------------------------
    @http.route('/bak/balance_sheet/data', type='json', auth='user')
    def balance_sheet_data(self, wizard_id, date_from=None, date_to=None,
                           target_move='posted', display_debit_credit=True,
                           enable_comparison=False, comparison_date_from=None,
                           comparison_date_to=None, **kwargs):
        env = request.env
        wizard = env['bak.balance.sheet.report'].browse(int(wizard_id))
        if not wizard.exists():
            wizard = env['bak.balance.sheet.report'].create({})

        vals = {
            'target_move': target_move,
            'display_debit_credit': display_debit_credit,
            'enable_comparison': enable_comparison,
            'date_from': date_from or False,
            'date_to': date_to or fields.Date.today(),
        }
        if enable_comparison:
            vals['comparison_date_from'] = comparison_date_from or False
            vals['comparison_date_to']   = comparison_date_to or False

        wizard.write(vals)
        return wizard.get_report_data()

    # ------------------------------------------------------------------
    # PDF export
    # ------------------------------------------------------------------
    @http.route('/bak/balance_sheet/pdf', type='http', auth='user')
    def balance_sheet_pdf(self, wizard_id, **kwargs):
        env = request.env
        wizard = env['bak.balance.sheet.report'].browse(int(wizard_id))
        if not wizard.exists():
            return Response('Wizard not found', status=404)

        data = wizard.get_report_data()
        html = self._build_pdf_html(data)

        try:
            pdf_content, _ = request.env['ir.actions.report']._run_wkhtmltopdf(
                [html],
                header=None, footer=None, landscape=False,
                specific_paperformat_args={
                    'data-report-margin-top': 10,
                    'data-report-header-spacing': 10,
                },
                unlink_inputs=True,
            )
        except Exception as e:
            _logger.error("PDF generation failed: %s", e)
            return Response(f'PDF generation failed: {e}',
                            content_type='text/plain', status=500)

        filename = 'Balance_Sheet_%s.pdf' % data.get('date_to', '')
        return request.make_response(
            pdf_content,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', content_disposition(filename)),
            ]
        )

    def _build_pdf_html(self, data):
        sym = data.get('currency_symbol', '')
        show_dc   = data.get('display_debit_credit', False)
        show_comp = data.get('enable_comparison', False)

        def fmt(n):
            if not n:
                return f'{sym} 0.00'
            sign = '-' if n < 0 else ''
            return f'{sign}{sym} {abs(n):,.2f}'

        def row_html(r):
            neg = ' class="negative"' if r.get('balance', 0) < 0 else ''
            h = f'<td>{r.get("code","")}</td><td class="indent">{r["name"]}</td>'
            if show_dc:
                h += f'<td class="num">{fmt(r.get("debit",0))}</td>'
                h += f'<td class="num">{fmt(r.get("credit",0))}</td>'
            h += f'<td class="num"{neg}>{fmt(r.get("balance",0))}</td>'
            if show_comp:
                cn = ' class="negative"' if r.get('comp_balance', 0) < 0 else ''
                h += f'<td class="num"{cn}>{fmt(r.get("comp_balance",0))}</td>'
            return f'<tr>{h}</tr>'

        def section_html(title, subs, total, comp_total):
            h = f'<tr class="section-header"><td colspan="10">{title.upper()}</td></tr>'
            for sub in subs:
                h += f'<tr class="subsection-header"><td colspan="10">{sub["name"]}</td></tr>'
                for r in sub.get('rows', []):
                    h += row_html(r)
                neg = ' class="negative"' if sub.get('subtotal', 0) < 0 else ''
                st = f'<tr class="subtotal"><td></td><td>Total {sub["name"]}</td>'
                if show_dc: st += '<td></td><td></td>'
                st += f'<td class="num"{neg}>{fmt(sub.get("subtotal",0))}</td>'
                if show_comp: st += f'<td class="num">{fmt(sub.get("comp_subtotal",0))}</td>'
                h += st + '</tr>'
            gt = f'<tr class="grand-total"><td></td><td>Total {title.title()}</td>'
            if show_dc: gt += '<td></td><td></td>'
            gt += f'<td class="num">{fmt(total)}</td>'
            if show_comp: gt += f'<td class="num">{fmt(comp_total)}</td>'
            h += gt + '</tr>'
            h += f'<tr><td colspan="10" style="height:8px"></td></tr>'
            return h

        col_headers = '<th>Code</th><th>Account</th>'
        if show_dc:
            col_headers += '<th class="num">Debit</th><th class="num">Credit</th>'
        col_headers += f'<th class="num">As of {data.get("date_to","")}</th>'
        if show_comp:
            col_headers += f'<th class="num">As of {data.get("comparison_date_to","")}</th>'

        body = section_html('Assets', data.get('assets', []),
                            data.get('total_assets', 0),
                            data.get('comp_total_assets', 0))
        body += section_html('Liabilities', data.get('liabilities', []),
                             data.get('total_liabilities', 0),
                             data.get('comp_total_liabilities', 0))
        body += section_html('Equity', data.get('equity', []),
                             data.get('total_equity', 0),
                             data.get('comp_total_equity', 0))

        le = f'<tr class="liab-equity-total"><td></td><td>LIABILITIES + EQUITY</td>'
        if show_dc: le += '<td></td><td></td>'
        le += f'<td class="num">{fmt(data.get("total_liabilities_equity",0))}</td>'
        if show_comp: le += f'<td class="num">{fmt(data.get("comp_total_liabilities_equity",0))}</td>'
        le += '</tr>'
        body += le

        return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"/>
<style>
body{{font-family:Arial,sans-serif;font-size:11px;margin:20px}}
h1{{text-align:center;font-size:15px;margin-bottom:2px}}
.sub{{text-align:center;color:#555;margin-bottom:14px;font-size:11px}}
table{{width:100%;border-collapse:collapse}}
th{{background:#4B4B6E;color:#fff;padding:6px 8px;text-align:left;font-size:10px;text-transform:uppercase}}
td{{padding:4px 8px;border-bottom:1px solid #eee}}
.section-header td{{background:#D9D9E8;font-weight:bold;padding:7px 8px}}
.subsection-header td{{font-weight:600;padding:5px 8px 3px 20px;color:#4B4B6E}}
.subtotal td{{font-weight:bold;border-top:1px solid #aaa;background:#fafafa}}
.grand-total td{{font-weight:bold;background:#B8B8D0;border-top:2px solid #666}}
.liab-equity-total td{{font-weight:bold;background:#4B4B6E;color:#fff;border-top:2px solid #333}}
.num{{text-align:right}}.negative{{color:#c00}}.indent{{padding-left:22px}}
</style></head><body>
<h1>{data.get('company_name','')} &mdash; Balance Sheet</h1>
<p class="sub">As of {data.get('date_to','')}
{'&nbsp;|&nbsp; From ' + data['date_from'] if data.get('date_from') else ''}
&nbsp;|&nbsp; {'Posted Entries' if data.get('target_move')=='posted' else 'All Entries'}
</p>
<table><thead><tr>{col_headers}</tr></thead><tbody>{body}</tbody></table>
</body></html>"""

    # ------------------------------------------------------------------
    # XLSX export
    # ------------------------------------------------------------------
    @http.route('/bak/balance_sheet/xlsx', type='http', auth='user')
    def balance_sheet_xlsx(self, wizard_id, **kwargs):
        try:
            import xlsxwriter
        except ImportError:
            return Response('xlsxwriter not installed. Run: pip3 install xlsxwriter',
                            content_type='text/plain', status=500)

        env = request.env
        wizard = env['bak.balance.sheet.report'].browse(int(wizard_id))
        if not wizard.exists():
            return Response('Wizard not found', status=404)

        data   = wizard.get_report_data()
        output = io.BytesIO()
        wb     = xlsxwriter.Workbook(output, {'in_memory': True})
        ws     = wb.add_worksheet('Balance Sheet')

        bold     = wb.add_format({'bold': True})
        hdr_fmt  = wb.add_format({'bold': True, 'bg_color': '#4B4B6E',
                                   'font_color': 'white', 'border': 1})
        sec_fmt  = wb.add_format({'bold': True, 'bg_color': '#D9D9E8', 'border': 1})
        sub_fmt  = wb.add_format({'bold': True, 'num_format': '#,##0.00', 'border': 1})
        num_fmt  = wb.add_format({'num_format': '#,##0.00'})
        tot_fmt  = wb.add_format({'bold': True, 'bg_color': '#B8B8D0',
                                   'num_format': '#,##0.00', 'border': 1})
        le_fmt   = wb.add_format({'bold': True, 'bg_color': '#4B4B6E',
                                   'font_color': 'white',
                                   'num_format': '#,##0.00', 'border': 1})

        show_dc   = data.get('display_debit_credit', False)
        show_comp = data.get('enable_comparison', False)

        ws.set_column(0, 0, 10)
        ws.set_column(1, 1, 42)
        col = 2
        if show_dc:
            ws.set_column(col, col + 1, 18)
            col += 2
        ws.set_column(col, col, 18)
        if show_comp:
            ws.set_column(col + 1, col + 1, 18)

        row = 0
        total_cols = 2 + (2 if show_dc else 0) + 1 + (1 if show_comp else 0)
        ws.merge_range(row, 0, row, total_cols - 1, 'Balance Sheet', hdr_fmt)
        row += 1
        bal_col = 2 + (2 if show_dc else 0)
        ws.write(row, bal_col, f'As of {data["date_to"]}', bold)
        if show_comp and data.get('comparison_date_to'):
            ws.write(row, bal_col + 1, f'As of {data["comparison_date_to"]}', bold)
        row += 2

        def write_section(title, subs, total, comp_total):
            nonlocal row
            ws.merge_range(row, 0, row, total_cols - 1, title.upper(), sec_fmt)
            row += 1
            for sub in subs:
                ws.write(row, 1, sub['name'], bold)
                row += 1
                for r in sub.get('rows', []):
                    c = 2
                    ws.write(row, 0, r.get('code', ''))
                    ws.write(row, 1, r['name'])
                    if show_dc:
                        ws.write(row, c, r.get('debit', 0), num_fmt)
                        ws.write(row, c + 1, r.get('credit', 0), num_fmt)
                        c += 2
                    ws.write(row, c, r.get('balance', 0), num_fmt)
                    if show_comp:
                        ws.write(row, c + 1, r.get('comp_balance', 0), num_fmt)
                    row += 1
                c = 2
                ws.write(row, 1, f'Total {sub["name"]}', sub_fmt)
                if show_dc: c += 2
                ws.write(row, c, sub.get('subtotal', 0), sub_fmt)
                if show_comp:
                    ws.write(row, c + 1, sub.get('comp_subtotal', 0), sub_fmt)
                row += 1
            c = 2
            ws.write(row, 1, f'Total {title.title()}', tot_fmt)
            if show_dc: c += 2
            ws.write(row, c, total, tot_fmt)
            if show_comp:
                ws.write(row, c + 1, comp_total, tot_fmt)
            row += 2

        write_section('Assets', data.get('assets', []),
                      data.get('total_assets', 0), data.get('comp_total_assets', 0))
        write_section('Liabilities', data.get('liabilities', []),
                      data.get('total_liabilities', 0), data.get('comp_total_liabilities', 0))
        write_section('Equity', data.get('equity', []),
                      data.get('total_equity', 0), data.get('comp_total_equity', 0))

        c = 2
        ws.write(row, 1, 'LIABILITIES + EQUITY', le_fmt)
        if show_dc: c += 2
        ws.write(row, c, data.get('total_liabilities_equity', 0), le_fmt)
        if show_comp:
            ws.write(row, c + 1, data.get('comp_total_liabilities_equity', 0), le_fmt)

        wb.close()
        output.seek(0)
        filename = f'Balance_Sheet_{data.get("date_to","")}.xlsx'
        return request.make_response(
            output.read(),
            headers=[
                ('Content-Type',
                 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', content_disposition(filename)),
            ]
        )

    # ------------------------------------------------------------------
    # DEBUG endpoint — remove after confirming schema
    # Visit: /bak/balance_sheet/debug_schema
    # ------------------------------------------------------------------
    @http.route('/bak/balance_sheet/debug_schema', type='http', auth='user')
    def debug_schema(self, **kwargs):
        cr = request.env.cr

        cr.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'account_account'
            ORDER BY ordinal_position
        """)
        aa_cols = cr.fetchall()

        cr.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_name ILIKE '%account%code%'
               OR table_name ILIKE '%account_account%'
            ORDER BY table_name
        """)
        tables = cr.fetchall()

        cr.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'account_move_line'
              AND column_name IN ('balance', 'amount_currency', 'debit', 'credit', 'company_id')
            ORDER BY column_name
        """)
        aml_cols = cr.fetchall()

        html = '<h2>account_account columns</h2><pre>'
        html += '\n'.join(f'{c[0]:40s} {c[1]}' for c in aa_cols)
        html += '</pre><h2>Related tables</h2><pre>'
        html += '\n'.join(t[0] for t in tables)
        html += '</pre><h2>account_move_line key columns</h2><pre>'
        html += '\n'.join(f'{c[0]:40s} {c[1]}' for c in aml_cols)
        html += '</pre>'
        return request.make_response(html, headers=[('Content-Type', 'text/html')])
