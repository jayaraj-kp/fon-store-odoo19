# -*- coding: utf-8 -*-
import json
import io
from odoo import http, fields
from odoo.http import request, content_disposition
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

        return request.render(
            'bak_balance_sheet_report.balance_sheet_inline_template',
            {'wizard': wizard}
        )

    # ------------------------------------------------------------------
    # JSON endpoint – fetch report data (used by JS for live filtering)
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

        # Write filter values
        vals = {
            'target_move': target_move,
            'display_debit_credit': display_debit_credit,
            'enable_comparison': enable_comparison,
        }
        if date_from:
            vals['date_from'] = date_from
        else:
            vals['date_from'] = False
        if date_to:
            vals['date_to'] = date_to
        else:
            vals['date_to'] = fields.Date.today()
        if enable_comparison:
            vals['comparison_date_from'] = comparison_date_from or False
            vals['comparison_date_to'] = comparison_date_to or False

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
            return request.not_found()

        data = wizard.get_report_data()
        html = request.env['ir.ui.view']._render_template(
            'bak_balance_sheet_report.balance_sheet_pdf_template',
            {'data': data}
        )

        pdf_content, _ = request.env['ir.actions.report']._run_wkhtmltopdf(
            [html],
            header=None,
            footer=None,
            landscape=False,
            specific_paperformat_args={
                'data-report-margin-top': 10,
                'data-report-header-spacing': 10,
            },
            unlink_inputs=True,
        )

        filename = 'Balance_Sheet_%s.pdf' % (data.get('date_to', ''))
        return request.make_response(
            pdf_content,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', content_disposition(filename)),
            ]
        )

    # ------------------------------------------------------------------
    # XLSX export
    # ------------------------------------------------------------------
    @http.route('/bak/balance_sheet/xlsx', type='http', auth='user')
    def balance_sheet_xlsx(self, wizard_id, **kwargs):
        try:
            import xlsxwriter
        except ImportError:
            return request.make_response(
                'xlsxwriter not installed',
                headers=[('Content-Type', 'text/plain')]
            )

        env = request.env
        wizard = env['bak.balance.sheet.report'].browse(int(wizard_id))
        if not wizard.exists():
            return request.not_found()

        data = wizard.get_report_data()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Balance Sheet')

        # Formats
        bold = workbook.add_format({'bold': True})
        header_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#4B4B6E', 'font_color': 'white',
            'border': 1
        })
        section_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#D9D9E8', 'border': 1
        })
        subtotal_fmt = workbook.add_format({
            'bold': True, 'num_format': '#,##0.00', 'border': 1
        })
        number_fmt = workbook.add_format({'num_format': '#,##0.00'})
        total_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#B8B8D0',
            'num_format': '#,##0.00', 'border': 1
        })

        # Column widths
        sheet.set_column(0, 0, 10)
        sheet.set_column(1, 1, 40)
        show_dc = data.get('display_debit_credit', False)
        show_comp = data.get('enable_comparison', False)

        col = 2
        if show_dc:
            sheet.set_column(col, col, 18)
            sheet.set_column(col + 1, col + 1, 18)
            col += 2
        sheet.set_column(col, col, 18)
        if show_comp:
            sheet.set_column(col + 1, col + 1, 18)

        # Title
        row = 0
        sheet.merge_range(row, 0, row, col + (1 if show_comp else 0),
                          'Balance Sheet', header_fmt)
        row += 1
        sheet.write(row, col, 'As of %s' % data['date_to'], bold)
        if show_comp and data.get('comparison_date_to'):
            sheet.write(row, col + 1, 'As of %s' % data['comparison_date_to'], bold)
        row += 2

        def write_section(title, subsections, total, comp_total):
            nonlocal row
            # Section header
            sheet.merge_range(row, 0, row, col + (1 if show_comp else 0),
                              title.upper(), section_fmt)
            row += 1

            for sub in subsections:
                # Subsection name
                sheet.write(row, 1, sub['name'], bold)
                row += 1

                for r in sub['rows']:
                    c = 2
                    sheet.write(row, 0, r.get('code', ''))
                    sheet.write(row, 1, r['name'])
                    if show_dc:
                        sheet.write(row, c, r.get('debit', 0), number_fmt)
                        sheet.write(row, c + 1, r.get('credit', 0), number_fmt)
                        c += 2
                    sheet.write(row, c, r['balance'], number_fmt)
                    if show_comp:
                        sheet.write(row, c + 1, r.get('comp_balance', 0), number_fmt)
                    row += 1

                # Subtotal row
                c = 2
                sheet.write(row, 1, 'Total %s' % sub['name'], subtotal_fmt)
                if show_dc:
                    c += 2
                sheet.write(row, c, sub['subtotal'], subtotal_fmt)
                if show_comp:
                    sheet.write(row, c + 1, sub.get('comp_subtotal', 0), subtotal_fmt)
                row += 1

            # Grand total
            c = 2
            if show_dc:
                c += 2
            sheet.write(row, 1, 'Total %s' % title.title(), total_fmt)
            sheet.write(row, c, total, total_fmt)
            if show_comp:
                sheet.write(row, c + 1, comp_total, total_fmt)
            row += 2

        write_section('Assets', data['assets'], data['total_assets'], data.get('comp_total_assets', 0))
        write_section('Liabilities', data['liabilities'], data['total_liabilities'], data.get('comp_total_liabilities', 0))
        write_section('Equity', data['equity'], data['total_equity'], data.get('comp_total_equity', 0))

        # Liabilities + Equity total
        c = 2
        if show_dc:
            c += 2
        sheet.write(row, 1, 'LIABILITIES + EQUITY', total_fmt)
        sheet.write(row, c, data['total_liabilities_equity'], total_fmt)
        if show_comp:
            sheet.write(row, c + 1, data.get('comp_total_liabilities_equity', 0), total_fmt)

        workbook.close()
        output.seek(0)
        filename = 'Balance_Sheet_%s.xlsx' % data.get('date_to', '')
        return request.make_response(
            output.read(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', content_disposition(filename)),
            ]
        )
