# -*- coding: utf-8 -*-
import io
from odoo import http, fields
from odoo.http import request, content_disposition, Response
import logging

_logger = logging.getLogger(__name__)


class ProfitLossController(http.Controller):

    # ------------------------------------------------------------------
    # Main HTML page
    # ------------------------------------------------------------------
    @http.route('/bak/profit_loss', type='http', auth='user', website=False)
    def profit_loss_main(self, wizard_id=None, **kwargs):
        env = request.env
        if wizard_id:
            wizard = env['bak.profit.loss.report'].browse(int(wizard_id))
            if not wizard.exists():
                wizard = env['bak.profit.loss.report'].create({})
        else:
            wizard = env['bak.profit.loss.report'].create({})

        date_to   = str(wizard.date_to or fields.Date.today())
        date_from = str(wizard.date_from) if wizard.date_from else ''

        html = self._render_page(wizard.id, date_to, date_from,
                                 wizard.target_move,
                                 wizard.display_debit_credit)
        return Response(html, content_type='text/html;charset=utf-8', status=200)

    def _render_page(self, wizard_id, date_to, date_from, target_move, display_debit_credit):
        css_url = '/bak_profit_loss_report/static/src/css/profit_loss.css'
        js_url  = '/bak_profit_loss_report/static/src/js/profit_loss_action.js'
        dc_val  = 'true' if display_debit_credit else 'false'

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <title>Profit &amp; Loss</title>
    <link rel="stylesheet" href="{css_url}"/>
    <style>body {{ margin:0; padding:0; background:#F5F5F8; }}</style>
</head>
<body>
<div id="bak_pl_app"
     data-wizard-id="{wizard_id}"
     data-date-to="{date_to}"
     data-date-from="{date_from}"
     data-target-move="{target_move}"
     data-display-dc="{dc_val}">

    <!-- TOP BAR -->
    <div class="bak-pl-topbar">
        <div class="bak-pl-topbar-left">
            <a href="/odoo/accounting" class="bak-pl-back">&#8592; Accounting</a>
            <span class="bak-pl-title">Profit &amp; Loss</span>
        </div>
        <div class="bak-pl-topbar-right">
            <button class="bak-btn bak-btn-outline" id="btn_pdf">&#128438; PDF</button>
            <button class="bak-btn bak-btn-outline" id="btn_xlsx">&#128202; XLSX</button>
            <button class="bak-btn bak-btn-outline" id="btn_comparison">&#8646; Comparison</button>
            <select class="bak-select" id="sel_moves">
                <option value="posted">Posted Entries</option>
                <option value="all">All Entries</option>
            </select>
        </div>
    </div>

    <!-- FILTER BAR -->
    <div class="bak-pl-filterbar">
        <div class="bak-filter-group">
            <label>From Date</label>
            <input type="date" id="flt_date_from" class="bak-input"/>
        </div>
        <div class="bak-filter-group">
            <label>To Date</label>
            <input type="date" id="flt_date_to" class="bak-input"/>
        </div>
        <div class="bak-filter-group">
            <label class="bak-check-label">
                <input type="checkbox" id="chk_dc"/> Show Debit/Credit
            </label>
        </div>
        <div class="bak-filter-group" id="grp_comparison" style="display:none">
            <label>Compare From</label>
            <input type="date" id="flt_comp_date_from" class="bak-input"/>
        </div>
        <div class="bak-filter-group" id="grp_comparison_to" style="display:none">
            <label>Compare To</label>
            <input type="date" id="flt_comp_date_to" class="bak-input"/>
        </div>
        <div class="bak-filter-group">
            <button class="bak-btn bak-btn-primary" id="btn_apply">&#8635; Apply</button>
        </div>
    </div>

    <!-- REPORT CONTENT -->
    <div class="bak-pl-body">
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
    # JSON endpoint
    # ------------------------------------------------------------------
    @http.route('/bak/profit_loss/data', type='json', auth='user')
    def profit_loss_data(self, wizard_id, date_from=None, date_to=None,
                         target_move='posted', display_debit_credit=False,
                         enable_comparison=False, comparison_date_from=None,
                         comparison_date_to=None, **kwargs):
        env    = request.env
        wizard = env['bak.profit.loss.report'].browse(int(wizard_id))
        if not wizard.exists():
            wizard = env['bak.profit.loss.report'].create({})

        vals = {
            'target_move':          target_move,
            'display_debit_credit': display_debit_credit,
            'enable_comparison':    enable_comparison,
            'date_from':            date_from or False,
            'date_to':              date_to   or fields.Date.today(),
        }
        if enable_comparison:
            vals['comparison_date_from'] = comparison_date_from or False
            vals['comparison_date_to']   = comparison_date_to   or False

        wizard.write(vals)
        return wizard.get_report_data()

    # ------------------------------------------------------------------
    # PDF export  (Odoo 19: _run_wkhtmltopdf returns bytes directly)
    # ------------------------------------------------------------------
    @http.route('/bak/profit_loss/pdf', type='http', auth='user')
    def profit_loss_pdf(self, wizard_id, **kwargs):
        env    = request.env
        wizard = env['bak.profit.loss.report'].browse(int(wizard_id))
        if not wizard.exists():
            return Response('Wizard not found', status=404)

        data = wizard.get_report_data()
        html = self._build_pdf_html(data)

        try:
            pdf_content = request.env['ir.actions.report']._run_wkhtmltopdf(
                [html],
                header=None, footer=None, landscape=False,
                specific_paperformat_args={
                    'data-report-margin-top': 10,
                    'data-report-header-spacing': 10,
                },
            )
        except Exception as e:
            _logger.error("P&L PDF generation failed: %s", e)
            return Response(f'PDF generation failed: {e}',
                            content_type='text/plain', status=500)

        filename = 'Profit_Loss_%s_%s.pdf' % (
            data.get('date_from', '') or '', data.get('date_to', ''))
        return request.make_response(
            pdf_content,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', content_disposition(filename)),
            ]
        )

    # ------------------------------------------------------------------
    # PDF HTML builder
    # ------------------------------------------------------------------
    def _build_pdf_html(self, data):
        show_dc   = data.get('display_debit_credit', False)
        show_comp = data.get('enable_comparison', False)
        sym       = data.get('currency_symbol', '')

        def fmt(n):
            if n is None:
                return ''
            sign = '-' if n < 0 else ''
            return f"{sign}{sym} {abs(n):,.2f}"

        def neg_cls(n):
            return ' class="negative"' if n < 0 else ''

        # Build column headers
        col_headers = '<th>Code</th><th>Account</th>'
        if show_dc:
            col_headers += '<th class="num">Debit</th><th class="num">Credit</th>'
        col_headers += '<th class="num">Amount</th>'
        if show_comp:
            col_headers += f'<th class="num">Comp ({data.get("comparison_date_to","")})</th>'

        body = ''
        ncols = 2 + (2 if show_dc else 0) + 1 + (1 if show_comp else 0)

        def section_html(title, subsections, total, comp_total, cls='section-header'):
            nonlocal body
            body += f'<tr class="{cls}"><td colspan="{ncols}">{title.upper()}</td></tr>'
            for sub in subsections:
                body += f'<tr class="subsection-header"><td colspan="{ncols}">{sub["name"]}</td></tr>'
                for row in sub.get('rows', []):
                    body += '<tr class="account-row">'
                    body += f'<td class="col-code">{row.get("code","")}</td>'
                    body += f'<td class="indent">{row["name"]}</td>'
                    if show_dc:
                        body += f'<td class="num">{fmt(row.get("debit",0))}</td>'
                        body += f'<td class="num">{fmt(row.get("credit",0))}</td>'
                    body += f'<td class="num"{neg_cls(row["balance"])}>{fmt(row["balance"])}</td>'
                    if show_comp:
                        body += f'<td class="num"{neg_cls(row["comp_balance"])}>{fmt(row["comp_balance"])}</td>'
                    body += '</tr>'
                # subtotal
                body += '<tr class="subtotal">'
                body += f'<td></td><td>Total {sub["name"]}</td>'
                if show_dc: body += '<td></td><td></td>'
                body += f'<td class="num"{neg_cls(sub["subtotal"])}>{fmt(sub["subtotal"])}</td>'
                if show_comp:
                    body += f'<td class="num"{neg_cls(sub["comp_subtotal"])}>{fmt(sub["comp_subtotal"])}</td>'
                body += '</tr>'
            # section total
            body += f'<tr class="grand-total"><td></td><td>TOTAL {title.upper()}</td>'
            if show_dc: body += '<td></td><td></td>'
            body += f'<td class="num"{neg_cls(total)}>{fmt(total)}</td>'
            if show_comp:
                body += f'<td class="num"{neg_cls(comp_total)}>{fmt(comp_total)}</td>'
            body += '</tr>'

        def summary_row(title, value, comp_value, row_cls):
            nonlocal body
            body += f'<tr class="{row_cls}"><td></td><td>{title}</td>'
            if show_dc: body += '<td></td><td></td>'
            body += f'<td class="num"{neg_cls(value)}>{fmt(value)}</td>'
            if show_comp:
                body += f'<td class="num"{neg_cls(comp_value)}>{fmt(comp_value)}</td>'
            body += '</tr>'
            # spacer
            body += f'<tr><td colspan="{ncols}" style="height:6px"></td></tr>'

        section_html('Revenue',              data.get('revenue', []),
                     data['total_revenue'],  data.get('comp_total_revenue', 0))
        body += f'<tr><td colspan="{ncols}" style="height:6px"></td></tr>'

        section_html('Cost of Revenue',      data.get('cogs', []),
                     data['total_cogs'],     data.get('comp_total_cogs', 0))
        body += f'<tr><td colspan="{ncols}" style="height:4px"></td></tr>'

        summary_row('GROSS PROFIT',
                    data['gross_profit'], data.get('comp_gross_profit', 0),
                    'gross-profit-row')

        section_html('Operating Expenses',   data.get('opex', []),
                     data['total_opex'],     data.get('comp_total_opex', 0))
        body += f'<tr><td colspan="{ncols}" style="height:4px"></td></tr>'

        summary_row('NET PROFIT',
                    data['net_profit'], data.get('comp_net_profit', 0),
                    'net-profit-row')

        period = f"From {data.get('date_from','')} to {data.get('date_to','')}" \
                 if data.get('date_from') else f"As of {data.get('date_to','')}"

        return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"/>
<style>
body{{font-family:Arial,sans-serif;font-size:11px;margin:20px}}
h1{{text-align:center;font-size:15px;margin-bottom:2px}}
.sub{{text-align:center;color:#555;margin-bottom:14px;font-size:11px}}
table{{width:100%;border-collapse:collapse}}
th{{background:#2E5266;color:#fff;padding:6px 8px;text-align:left;font-size:10px;text-transform:uppercase}}
td{{padding:4px 8px;border-bottom:1px solid #eee}}
.section-header td{{background:#C8D8E4;font-weight:bold;padding:7px 8px;color:#2E5266}}
.subsection-header td{{font-weight:600;padding:5px 8px 3px 20px;color:#2E5266}}
.account-row:hover td{{background:#f7f9fb}}
.subtotal td{{font-weight:bold;border-top:1px solid #aaa;background:#fafafa}}
.grand-total td{{font-weight:bold;background:#A3BFCF;border-top:2px solid #666;color:#1a3a4a}}
.gross-profit-row td{{font-weight:bold;background:#D4EDDA;color:#155724;border-top:2px solid #28a745;padding:7px 8px}}
.net-profit-row td{{font-weight:bold;background:#2E5266;color:#fff;border-top:2px solid #1a3342;padding:9px 8px;font-size:12px}}
.num{{text-align:right}}.negative{{color:#c00}}
.col-code{{width:60px;font-size:10px;color:#777}}
.indent{{padding-left:22px}}
</style></head><body>
<h1>{data.get('company_name','')} &mdash; Profit &amp; Loss</h1>
<p class="sub">{period} &nbsp;|&nbsp;
{'Posted Entries' if data.get('target_move')=='posted' else 'All Entries'}</p>
<table><thead><tr>{col_headers}</tr></thead><tbody>{body}</tbody></table>
</body></html>"""

    # ------------------------------------------------------------------
    # XLSX export
    # ------------------------------------------------------------------
    @http.route('/bak/profit_loss/xlsx', type='http', auth='user')
    def profit_loss_xlsx(self, wizard_id, **kwargs):
        try:
            import xlsxwriter
        except ImportError:
            return Response('xlsxwriter not installed. Run: pip3 install xlsxwriter',
                            content_type='text/plain', status=500)

        env    = request.env
        wizard = env['bak.profit.loss.report'].browse(int(wizard_id))
        if not wizard.exists():
            return Response('Wizard not found', status=404)

        data   = wizard.get_report_data()
        output = io.BytesIO()
        wb     = xlsxwriter.Workbook(output, {'in_memory': True})
        ws     = wb.add_worksheet('Profit & Loss')

        show_dc   = data.get('display_debit_credit', False)
        show_comp = data.get('enable_comparison', False)
        sym       = data.get('currency_symbol', '')

        # Formats
        title_fmt   = wb.add_format({'bold': True, 'font_size': 13, 'align': 'center',
                                      'bg_color': '#2E5266', 'font_color': 'white', 'border': 1})
        hdr_fmt     = wb.add_format({'bold': True, 'bg_color': '#2E5266',
                                      'font_color': 'white', 'border': 1, 'font_size': 9,
                                      'text_wrap': True})
        sec_fmt     = wb.add_format({'bold': True, 'bg_color': '#C8D8E4',
                                      'font_color': '#2E5266', 'border': 1})
        subsec_fmt  = wb.add_format({'bold': True, 'italic': True, 'indent': 1})
        num_fmt     = wb.add_format({'num_format': f'"{sym}" #,##0.00'})
        neg_fmt     = wb.add_format({'num_format': f'"{sym}" #,##0.00', 'font_color': '#C0392B'})
        sub_fmt     = wb.add_format({'bold': True, 'num_format': f'"{sym}" #,##0.00',
                                      'top': 1, 'bg_color': '#fafafa'})
        sec_tot_fmt = wb.add_format({'bold': True, 'num_format': f'"{sym}" #,##0.00',
                                      'bg_color': '#A3BFCF', 'font_color': '#1a3a4a', 'border': 1})
        gp_lbl_fmt  = wb.add_format({'bold': True, 'bg_color': '#D4EDDA', 'font_color': '#155724',
                                      'top': 2, 'bottom': 1})
        gp_num_fmt  = wb.add_format({'bold': True, 'num_format': f'"{sym}" #,##0.00',
                                      'bg_color': '#D4EDDA', 'font_color': '#155724',
                                      'top': 2, 'bottom': 1})
        np_lbl_fmt  = wb.add_format({'bold': True, 'bg_color': '#2E5266', 'font_color': 'white',
                                      'top': 2, 'font_size': 11})
        np_num_fmt  = wb.add_format({'bold': True, 'num_format': f'"{sym}" #,##0.00',
                                      'bg_color': '#2E5266', 'font_color': 'white',
                                      'top': 2, 'font_size': 11})
        bold        = wb.add_format({'bold': True})

        # Column widths
        ws.set_column(0, 0, 10)   # code
        ws.set_column(1, 1, 42)   # name
        col = 2
        if show_dc:
            ws.set_column(col, col + 1, 18)
            col += 2
        ws.set_column(col, col, 18)
        if show_comp:
            ws.set_column(col + 1, col + 1, 18)

        total_cols = 2 + (2 if show_dc else 0) + 1 + (1 if show_comp else 0)
        row = 0

        # Title row
        ws.merge_range(row, 0, row, total_cols - 1,
                       f"{data['company_name']} — Profit & Loss", title_fmt)
        row += 1
        period = f"From {data.get('date_from','')} to {data.get('date_to','')}" \
                 if data.get('date_from') else f"As of {data.get('date_to','')}"
        ws.merge_range(row, 0, row, total_cols - 1, period, bold)
        row += 2

        # Header row
        ws.write(row, 0, 'Code', hdr_fmt)
        ws.write(row, 1, 'Account', hdr_fmt)
        c = 2
        if show_dc:
            ws.write(row, c, 'Debit', hdr_fmt); c += 1
            ws.write(row, c, 'Credit', hdr_fmt); c += 1
        ws.write(row, c, 'Amount', hdr_fmt); c += 1
        if show_comp:
            ws.write(row, c, f'Comp ({data.get("comparison_date_to","")})', hdr_fmt)
        row += 1

        bal_col = 2 + (2 if show_dc else 0)

        def write_section(title, subs, total, comp_total):
            nonlocal row
            ws.merge_range(row, 0, row, total_cols - 1, title.upper(), sec_fmt)
            row += 1
            for sub in subs:
                ws.merge_range(row, 0, row, total_cols - 1, sub['name'], subsec_fmt)
                row += 1
                for r in sub.get('rows', []):
                    ws.write(row, 0, r.get('code', ''))
                    ws.write(row, 1, '  ' + r['name'])
                    c = 2
                    if show_dc:
                        ws.write(row, c, r.get('debit', 0), num_fmt); c += 1
                        ws.write(row, c, r.get('credit', 0), num_fmt); c += 1
                    nf = neg_fmt if r['balance'] < 0 else num_fmt
                    ws.write(row, c, r['balance'], nf); c += 1
                    if show_comp:
                        nf2 = neg_fmt if r['comp_balance'] < 0 else num_fmt
                        ws.write(row, c, r['comp_balance'], nf2)
                    row += 1
                # subtotal
                ws.write(row, 1, f'Total {sub["name"]}', sub_fmt)
                c = 2
                if show_dc: c += 2
                ws.write(row, c, sub['subtotal'], sub_fmt); c += 1
                if show_comp: ws.write(row, c, sub.get('comp_subtotal', 0), sub_fmt)
                row += 1
            # section total
            ws.write(row, 1, f'Total {title.title()}', sec_tot_fmt)
            c = 2
            if show_dc: c += 2
            ws.write(row, c, total, sec_tot_fmt); c += 1
            if show_comp: ws.write(row, c, comp_total, sec_tot_fmt)
            row += 2

        def write_summary(title, value, comp_val, lbl_fmt, num_f):
            nonlocal row
            ws.write(row, 1, title, lbl_fmt)
            c = bal_col
            ws.write(row, c, value, num_f); c += 1
            if show_comp: ws.write(row, c, comp_val, num_f)
            row += 2

        write_section('Revenue',
                      data.get('revenue', []), data['total_revenue'], data.get('comp_total_revenue', 0))
        write_section('Cost of Revenue',
                      data.get('cogs', []),    data['total_cogs'],    data.get('comp_total_cogs', 0))
        write_summary('GROSS PROFIT',
                      data['gross_profit'], data.get('comp_gross_profit', 0), gp_lbl_fmt, gp_num_fmt)
        write_section('Operating Expenses',
                      data.get('opex', []),    data['total_opex'],    data.get('comp_total_opex', 0))
        write_summary('NET PROFIT',
                      data['net_profit'], data.get('comp_net_profit', 0), np_lbl_fmt, np_num_fmt)

        wb.close()
        output.seek(0)
        filename = f"Profit_Loss_{data.get('date_from','')}_to_{data.get('date_to','')}.xlsx"
        return request.make_response(
            output.read(),
            headers=[
                ('Content-Type',
                 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', content_disposition(filename)),
            ]
        )

    # ------------------------------------------------------------------
    # Debug schema (same as balance sheet — for troubleshooting)
    # ------------------------------------------------------------------
    @http.route('/bak/profit_loss/debug_schema', type='http', auth='user')
    def debug_schema(self, **kwargs):
        cr = request.env.cr
        cr.execute("""
            SELECT column_name, data_type FROM information_schema.columns
            WHERE table_name = 'account_account' ORDER BY ordinal_position
        """)
        aa_cols = cr.fetchall()
        html = '<h2>account_account columns</h2><pre>'
        html += '\n'.join(f'{c[0]:40s} {c[1]}' for c in aa_cols)
        html += '</pre>'
        return request.make_response(html, headers=[('Content-Type', 'text/html')])
