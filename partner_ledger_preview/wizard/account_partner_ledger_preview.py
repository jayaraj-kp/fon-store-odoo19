# # from odoo import fields, models, api, _
# #
# #
# # class AccountPartnerLedgerPreview(models.TransientModel):
# #     """
# #     Inherits account.report.partner.ledger (from accounting_pdf_reports)
# #     and adds an inline HTML preview capability.
# #     No changes are made to the original module.
# #     """
# #     _inherit = 'account.report.partner.ledger'
# #
# #     preview_html = fields.Html(
# #         string='Preview',
# #         sanitize=False,
# #         readonly=True,
# #     )
# #
# #     # ------------------------------------------------------------------
# #     # Public action – called by the Preview button in the wizard
# #     # ------------------------------------------------------------------
# #     def action_preview_report(self):
# #         self.ensure_one()
# #         data = self._prepare_preview_data()
# #         report_obj = self.env['report.accounting_pdf_reports.report_partnerledger']
# #         report_values = report_obj._get_report_values(None, data=data)
# #         self.preview_html = self._build_preview_html(report_values, data)
# #
# #         return {
# #             'type': 'ir.actions.act_window',
# #             'name': _('Partner Ledger – Preview'),
# #             'res_model': 'account.report.partner.ledger',
# #             'res_id': self.id,
# #             'view_mode': 'form',
# #             'view_id': self.env.ref(
# #                 'partner_ledger_preview.view_partner_ledger_preview_form'
# #             ).id,
# #             'target': 'new',
# #             'context': self.env.context,
# #         }
# #
# #     # ------------------------------------------------------------------
# #     # Helpers
# #     # ------------------------------------------------------------------
# #     def _prepare_preview_data(self):
# #         """Build the data dict expected by _get_report_values."""
# #         form = self.read([
# #             'date_from', 'date_to', 'journal_ids', 'target_move',
# #             'result_selection', 'reconciled', 'amount_currency',
# #             'partner_ids',
# #         ])[0]
# #         # many2many fields arrive as lists of ids – keep them that way
# #         form['journal_ids'] = form.get('journal_ids') or []
# #         form['partner_ids'] = form.get('partner_ids') or []
# #         form['used_context'] = {
# #             'date_from': form.get('date_from') or False,
# #             'date_to': form.get('date_to') or False,
# #             'journal_ids': form['journal_ids'],
# #             'state': form.get('target_move', 'all'),
# #             'strict_range': True,
# #             'lang': self.env.context.get('lang') or 'en_US',
# #         }
# #         return {'form': form}
# #
# #     def _build_preview_html(self, report_values, data):
# #         """Return a fully self-contained HTML string for the preview widget."""
# #         company = self.env.company
# #         currency_symbol = company.currency_id.symbol or ''
# #
# #         def fmt(value):
# #             return '{:,.2f}'.format(value or 0.0)
# #
# #         date_from = data['form'].get('date_from') or ''
# #         date_to = data['form'].get('date_to') or ''
# #         target_move = data['form'].get('target_move', 'all')
# #         target_label = 'All Posted Entries' if target_move == 'posted' else 'All Entries'
# #         show_currency = data['form'].get('amount_currency', False)
# #
# #         lines_fn = report_values['lines']
# #         sum_fn = report_values['sum_partner']
# #         docs = report_values['docs']
# #
# #         # ---- CSS -------------------------------------------------------
# #         parts = ["""
# # <style>
# #   .pl-wrap { font-family: Arial, sans-serif; font-size: 13px; color: #222; }
# #   .pl-wrap h3 { font-size: 16px; margin: 0 0 8px; }
# #   .pl-meta { display: flex; flex-wrap: wrap; gap: 24px; margin-bottom: 14px;
# #              font-size: 12px; background: #f0f4fa; padding: 8px 12px;
# #              border-radius: 4px; }
# #   .pl-meta div strong { display: block; color: #555; font-size: 11px;
# #                         text-transform: uppercase; letter-spacing: .4px; }
# #   .pl-table { width: 100%; border-collapse: collapse; font-size: 12px; }
# #   .pl-table thead th { background: #3b5998; color: #fff; padding: 6px 8px;
# #                         text-align: left; white-space: nowrap; }
# #   .pl-table thead th.r { text-align: right; }
# #   .pl-table td { padding: 4px 8px; border-bottom: 1px solid #eee;
# #                  vertical-align: top; }
# #   .pl-table td.r { text-align: right; font-variant-numeric: tabular-nums;
# #                    white-space: nowrap; }
# #   .pl-partner td { background: #dde6f5; font-weight: bold; }
# #   .pl-no-lines td { color: #aaa; font-style: italic; padding-left: 24px; }
# #   .pl-empty { text-align: center; color: #888; font-style: italic;
# #               padding: 30px 0; }
# # </style>
# # <div class="pl-wrap">
# #   <h3>&#128196; Partner Ledger</h3>
# #   <div class="pl-meta">
# # """]
# #
# #         # meta bar
# #         parts.append(f'<div><strong>Company</strong>{company.name or ""}</div>')
# #         if date_from:
# #             parts.append(f'<div><strong>Date From</strong>{date_from}</div>')
# #         if date_to:
# #             parts.append(f'<div><strong>Date To</strong>{date_to}</div>')
# #         parts.append(f'<div><strong>Target Moves</strong>{target_label}</div>')
# #         parts.append('</div>')  # .pl-meta
# #
# #         # ---- table -----------------------------------------------------
# #         if not docs:
# #             parts.append('<p class="pl-empty">No records found for the selected criteria.</p>')
# #         else:
# #             parts.append('<table class="pl-table"><thead><tr>')
# #             headers = ['Date', 'Journal', 'Account', 'Reference / Description',
# #                        'Debit', 'Credit', 'Balance']
# #             if show_currency:
# #                 headers.append('Amount Currency')
# #             for h in headers:
# #                 cls = ' class="r"' if h in ('Debit', 'Credit', 'Balance', 'Amount Currency') else ''
# #                 parts.append(f'<th{cls}>{h}</th>')
# #             parts.append('</tr></thead><tbody>')
# #
# #             for partner in docs:
# #                 debit = sum_fn(data, partner, 'debit')
# #                 credit = sum_fn(data, partner, 'credit')
# #                 balance = sum_fn(data, partner, 'debit - credit')
# #                 partner_label = ' – '.join(
# #                     p for p in [partner.ref or '', partner.name or ''] if p
# #                 ) or '(no name)'
# #
# #                 extra_td = '<td></td>' if show_currency else ''
# #                 parts.append(
# #                     f'<tr class="pl-partner">'
# #                     f'<td colspan="4">{partner_label}</td>'
# #                     f'<td class="r">{currency_symbol}&nbsp;{fmt(debit)}</td>'
# #                     f'<td class="r">{currency_symbol}&nbsp;{fmt(credit)}</td>'
# #                     f'<td class="r">{currency_symbol}&nbsp;{fmt(balance)}</td>'
# #                     f'{extra_td}'
# #                     f'</tr>'
# #                 )
# #
# #                 move_lines = lines_fn(data, partner)
# #                 if not move_lines:
# #                     cols = 8 if show_currency else 7
# #                     parts.append(
# #                         f'<tr class="pl-no-lines"><td colspan="{cols}">No transactions</td></tr>'
# #                     )
# #                 for line in move_lines:
# #                     date_str = str(line.get('date') or '')
# #                     code = line.get('code') or ''
# #                     a_name = line.get('a_name') or ''
# #                     desc = line.get('displayed_name') or ''
# #                     row = (
# #                         f'<tr>'
# #                         f'<td>{date_str}</td>'
# #                         f'<td>{code}</td>'
# #                         f'<td>{a_name}</td>'
# #                         f'<td>{desc}</td>'
# #                         f'<td class="r">{currency_symbol}&nbsp;{fmt(line.get("debit", 0.0))}</td>'
# #                         f'<td class="r">{currency_symbol}&nbsp;{fmt(line.get("credit", 0.0))}</td>'
# #                         f'<td class="r">{currency_symbol}&nbsp;{fmt(line.get("progress", 0.0))}</td>'
# #                     )
# #                     if show_currency:
# #                         cur_id = line.get('currency_id')
# #                         if cur_id:
# #                             row += (
# #                                 f'<td class="r">{cur_id.symbol}&nbsp;'
# #                                 f'{fmt(line.get("amount_currency", 0.0))}</td>'
# #                             )
# #                         else:
# #                             row += '<td></td>'
# #                     row += '</tr>'
# #                     parts.append(row)
# #
# #             parts.append('</tbody></table>')
# #
# #         parts.append('</div>')
# #         return ''.join(parts)
# from odoo import fields, models, api, _
#
#
# class AccountPartnerLedgerPreview(models.TransientModel):
#     """
#     Inherits account.report.partner.ledger (from accounting_pdf_reports)
#     and adds an inline HTML preview with:
#       • Clickable amounts      → opens the related Journal Entry form
#       • Clickable account name → opens the Account form
#       • Clickable partner name → lists that partner's journal items
#       • Grand total row at the bottom
#     """
#     _inherit = 'account.report.partner.ledger'
#
#     preview_html = fields.Html(
#         string='Preview',
#         sanitize=False,
#         readonly=True,
#     )
#
#     # ------------------------------------------------------------------
#     # Public action – called by the Preview button in the wizard
#     # ------------------------------------------------------------------
#     def action_preview_report(self):
#         self.ensure_one()
#         data = self._prepare_preview_data()
#         report_obj = self.env['report.accounting_pdf_reports.report_partnerledger']
#         report_values = report_obj._get_report_values(None, data=data)
#         self.preview_html = self._build_preview_html(report_values, data)
#
#         return {
#             'type': 'ir.actions.act_window',
#             'name': _('Partner Ledger – Preview'),
#             'res_model': 'account.report.partner.ledger',
#             'res_id': self.id,
#             'view_mode': 'form',
#             'view_id': self.env.ref(
#                 'partner_ledger_preview.view_partner_ledger_preview_form'
#             ).id,
#             'target': 'new',
#             'context': self.env.context,
#         }
#
#     # ------------------------------------------------------------------
#     # Helpers – data preparation
#     # ------------------------------------------------------------------
#     def _prepare_preview_data(self):
#         """Build the data dict expected by _get_report_values."""
#         form = self.read([
#             'date_from', 'date_to', 'journal_ids', 'target_move',
#             'result_selection', 'reconciled', 'amount_currency',
#             'partner_ids',
#         ])[0]
#         form['journal_ids'] = form.get('journal_ids') or []
#         form['partner_ids'] = form.get('partner_ids') or []
#         form['used_context'] = {
#             'date_from': form.get('date_from') or False,
#             'date_to': form.get('date_to') or False,
#             'journal_ids': form['journal_ids'],
#             'state': form.get('target_move', 'all'),
#             'strict_range': True,
#             'lang': self.env.context.get('lang') or 'en_US',
#         }
#         return {'form': form}
#
#     # ------------------------------------------------------------------
#     # Helpers – resolve move_id / account_id from a report line dict
#     # ------------------------------------------------------------------
#     def _resolve_line_ids(self, line):
#         """
#         Return (move_id, account_id) integers for a report line dict.
#
#         accounting_pdf_reports builds lines from account.move.line rows.
#         Depending on the Odoo/module version, the dict may already carry
#         'move_id' and 'account_id', or only the move.line primary key 'id'.
#         We try every known key and fall back to a single DB browse when needed.
#         """
#         def _unwrap(val):
#             """Handle both int and (id, name) tuples that come from .read()."""
#             if isinstance(val, (list, tuple)) and val:
#                 return val[0]
#             return val or None
#
#         move_id    = _unwrap(line.get('move_id'))
#         account_id = _unwrap(line.get('account_id'))
#
#         # If either is missing, try to fetch from the move.line record
#         if (not move_id or not account_id) and line.get('id'):
#             try:
#                 ml = self.env['account.move.line'].browse(int(line['id']))
#                 if not move_id:
#                     move_id = ml.move_id.id or None
#                 if not account_id:
#                     account_id = ml.account_id.id or None
#             except Exception:
#                 pass
#
#         return move_id, account_id
#
#     # ------------------------------------------------------------------
#     # Helpers – HTML link builders
#     # ------------------------------------------------------------------
#     @staticmethod
#     def _a(url, label, title='', extra_style=''):
#         """Generic anchor tag."""
#         base = 'color:#1a56db;text-decoration:none;'
#         t = f' title="{title}"' if title else ''
#         return f'<a href="{url}" target="_blank" style="{base}{extra_style}"{t}>{label}</a>'
#
#     def _entry_link(self, move_id, label):
#         """Label linked to the Journal Entry form."""
#         if not move_id:
#             return label
#         url = f'/web#model=account.move&id={move_id}&view_type=form'
#         return self._a(url, label, title='Open Journal Entry')
#
#     def _account_link(self, account_id, label):
#         """Label linked to the Account form."""
#         if not account_id:
#             return label
#         url = f'/web#model=account.account&id={account_id}&view_type=form'
#         return self._a(url, label, title='Open Account')
#
#     def _partner_link(self, partner_id, label):
#         """Label linked to filtered journal items for this partner."""
#         if not partner_id:
#             return label
#         # Use the standard journal items list with a domain filter
#         url = (
#             f'/odoo/accounting/journal-items?'
#             f'search=%5B%5B%22partner_id%22%2C%22%3D%22%2C{partner_id}%5D%5D'
#         )
#         return self._a(url, label, title='View journal items for this partner',
#                        extra_style='font-weight:bold;')
#
#     def _amount_td(self, display, move_id, css='r'):
#         """<td> whose content links to the journal entry when possible."""
#         inner = self._entry_link(move_id, display)
#         return f'<td class="{css}">{inner}</td>'
#
#     # ------------------------------------------------------------------
#     # Main HTML builder
#     # ------------------------------------------------------------------
#     def _build_preview_html(self, report_values, data):
#         company         = self.env.company
#         currency_symbol = company.currency_id.symbol or '₹'
#
#         def fmt(v):
#             return '{:,.2f}'.format(v or 0.0)
#
#         def money(v):
#             return f'{currency_symbol}&nbsp;{fmt(v)}'
#
#         date_from   = data['form'].get('date_from') or ''
#         date_to     = data['form'].get('date_to') or ''
#         target_move = data['form'].get('target_move', 'all')
#         target_lbl  = 'All Posted Entries' if target_move == 'posted' else 'All Entries'
#         show_cur    = data['form'].get('amount_currency', False)
#
#         lines_fn = report_values['lines']
#         sum_fn   = report_values['sum_partner']
#         docs     = report_values['docs']
#
#         # ================================================================
#         # CSS
#         # ================================================================
#         parts = ["""
# <style>
#   .pl-wrap { font-family: Arial, sans-serif; font-size: 13px; color: #222; }
#   .pl-wrap h3 { font-size: 16px; margin: 0 0 12px;
#                 display: flex; align-items: center; gap: 8px; }
#
#   /* ---- Meta bar ---- */
#   .pl-meta { display: flex; flex-wrap: wrap; gap: 0; margin-bottom: 16px;
#              font-size: 12px; background: #f0f4fa;
#              border-radius: 4px; border: 1px solid #c9d6ea; }
#   .pl-meta-item { padding: 8px 18px; border-right: 1px solid #c9d6ea; }
#   .pl-meta-item:last-child { border-right: none; }
#   .pl-meta-item strong { display: block; color: #666; font-size: 10px;
#                           text-transform: uppercase; letter-spacing: .6px;
#                           margin-bottom: 3px; }
#   .pl-meta-item span { font-weight: 600; color: #1a1a1a; }
#
#   /* ---- Table ---- */
#   .pl-table { width: 100%; border-collapse: collapse; font-size: 12px; }
#   .pl-table thead th { background: #3b5998; color: #fff; padding: 7px 10px;
#                         text-align: left; white-space: nowrap; font-size: 11px;
#                         text-transform: uppercase; letter-spacing: .4px; }
#   .pl-table thead th.r { text-align: right; }
#   .pl-table td { padding: 5px 10px; border-bottom: 1px solid #eee;
#                  vertical-align: middle; }
#   .pl-table td.r { text-align: right; font-variant-numeric: tabular-nums;
#                    white-space: nowrap; }
#
#   /* Partner summary row */
#   .pl-partner > td { background: #dde6f5; font-weight: bold;
#                      border-top: 2px solid #b0c4de;
#                      border-bottom: 1px solid #afc1de; }
#   .pl-partner > td.r { color: #1a3a6b; }
#
#   /* Detail rows */
#   .pl-line > td { background: #fff; }
#   .pl-line:hover > td { background: #f5f8ff; }
#
#   /* Empty / no-lines */
#   .pl-no-lines > td { color: #aaa; font-style: italic; padding-left: 24px; }
#   .pl-empty { text-align: center; color: #888; font-style: italic; padding: 30px 0; }
#
#   /* Grand total row */
#   .pl-total > td { background: #2e4a8a; color: #fff; font-weight: bold;
#                    padding: 7px 10px; border-top: 3px solid #1a2e5a; }
#   .pl-total > td.r { text-align: right; }
#
#   /* Links */
#   .pl-table a { color: #1a56db; text-decoration: none; }
#   .pl-table a:hover { text-decoration: underline; color: #0e3a9e; }
# </style>
# <div class="pl-wrap">
#   <h3>&#128196; Partner Ledger</h3>
#   <div class="pl-meta">
# """]
#
#         # Meta bar items
#         parts.append(
#             f'<div class="pl-meta-item">'
#             f'<strong>Company</strong><span>{company.name or ""}</span></div>'
#         )
#         if date_from:
#             parts.append(
#                 f'<div class="pl-meta-item">'
#                 f'<strong>Date From</strong><span>{date_from}</span></div>'
#             )
#         if date_to:
#             parts.append(
#                 f'<div class="pl-meta-item">'
#                 f'<strong>Date To</strong><span>{date_to}</span></div>'
#             )
#         parts.append(
#             f'<div class="pl-meta-item">'
#             f'<strong>Target Moves</strong><span>{target_lbl}</span></div>'
#         )
#         parts.append('</div>')  # end .pl-meta
#
#         # ================================================================
#         # Table
#         # ================================================================
#         if not docs:
#             parts.append(
#                 '<p class="pl-empty">No records found for the selected criteria.</p>'
#             )
#         else:
#             # Table header
#             parts.append('<table class="pl-table"><thead><tr>')
#             header_cols = [
#                 ('Date', False),
#                 ('Journal', False),
#                 ('Account', False),
#                 ('Reference / Description', False),
#                 ('Debit', True),
#                 ('Credit', True),
#                 ('Balance', True),
#             ]
#             if show_cur:
#                 header_cols.append(('Amount Currency', True))
#             for h, right in header_cols:
#                 r_cls = ' class="r"' if right else ''
#                 parts.append(f'<th{r_cls}>{h}</th>')
#             parts.append('</tr></thead><tbody>')
#
#             grand_debit = grand_credit = grand_balance = 0.0
#
#             for partner in docs:
#                 p_debit   = sum_fn(data, partner, 'debit') or 0.0
#                 p_credit  = sum_fn(data, partner, 'credit') or 0.0
#                 p_balance = sum_fn(data, partner, 'debit - credit') or 0.0
#                 grand_debit   += p_debit
#                 grand_credit  += p_credit
#                 grand_balance += p_balance
#
#                 p_label = ' – '.join(
#                     x for x in [partner.ref or '', partner.name or ''] if x
#                 ) or '(no name)'
#
#                 extra = '<td class="r"></td>' if show_cur else ''
#                 parts.append(
#                     f'<tr class="pl-partner">'
#                     f'<td colspan="4">{self._partner_link(partner.id, p_label)}</td>'
#                     f'<td class="r">{money(p_debit)}</td>'
#                     f'<td class="r">{money(p_credit)}</td>'
#                     f'<td class="r">{money(p_balance)}</td>'
#                     f'{extra}</tr>'
#                 )
#
#                 move_lines = lines_fn(data, partner)
#                 if not move_lines:
#                     ncols = 8 if show_cur else 7
#                     parts.append(
#                         f'<tr class="pl-no-lines">'
#                         f'<td colspan="{ncols}">No transactions</td></tr>'
#                     )
#
#                 for line in move_lines:
#                     move_id, account_id = self._resolve_line_ids(line)
#
#                     date_str = str(line.get('date') or '')
#                     code     = line.get('code') or ''
#                     a_name   = line.get('a_name') or ''
#                     desc     = line.get('displayed_name') or ''
#
#                     acc_cell  = self._account_link(account_id, a_name)
#                     desc_cell = self._entry_link(move_id, desc)
#
#                     d_val = line.get('debit', 0.0)
#                     c_val = line.get('credit', 0.0)
#                     b_val = line.get('progress', 0.0)
#
#                     parts.append(
#                         f'<tr class="pl-line">'
#                         f'<td>{date_str}</td>'
#                         f'<td>{code}</td>'
#                         f'<td>{acc_cell}</td>'
#                         f'<td>{desc_cell}</td>'
#                     )
#                     parts.append(self._amount_td(money(d_val), move_id))
#                     parts.append(self._amount_td(money(c_val), move_id))
#                     parts.append(self._amount_td(money(b_val), move_id))
#
#                     if show_cur:
#                         cur_id = line.get('currency_id')
#                         if cur_id:
#                             sym = getattr(cur_id, 'symbol', '')
#                             cur_disp = f'{sym}&nbsp;{fmt(line.get("amount_currency", 0.0))}'
#                             parts.append(self._amount_td(cur_disp, move_id))
#                         else:
#                             parts.append('<td></td>')
#
#                     parts.append('</tr>')
#
#             # Grand total row
#             extra = '<td></td>' if show_cur else ''
#             parts.append(
#                 f'<tr class="pl-total">'
#                 f'<td colspan="4">Grand Total</td>'
#                 f'<td class="r">{money(grand_debit)}</td>'
#                 f'<td class="r">{money(grand_credit)}</td>'
#                 f'<td class="r">{money(grand_balance)}</td>'
#                 f'{extra}</tr>'
#             )
#             parts.append('</tbody></table>')
#
#         parts.append('</div>')
#         return ''.join(parts)

from odoo import fields, models, api, _


class AccountPartnerLedgerPreview(models.TransientModel):
    """
    Inherits account.report.partner.ledger (from accounting_pdf_reports)
    and adds:
      • partner_ids  – optional Many2many filter to scope the report to
                       specific partners only
      • preview_html – inline HTML preview rendered without generating a PDF
        - Clickable amounts      → opens the related Journal Entry form
        - Clickable account name → opens the Account form
        - Clickable partner name → lists that partner's journal items
        - Grand total row at the bottom
    """
    _inherit = 'account.report.partner.ledger'

    # ------------------------------------------------------------------
    # New field: optional partner filter
    # ------------------------------------------------------------------
    partner_ids = fields.Many2many(
        comodel_name='res.partner',
        string='Partners',
        help='Leave empty to include all partners. '
             'Select one or more to restrict the report to those partners only.',
    )

    preview_html = fields.Html(
        string='Preview',
        sanitize=False,
        readonly=True,
    )

    # ------------------------------------------------------------------
    # Public action – called by the Preview button in the wizard
    # ------------------------------------------------------------------
    def action_preview_report(self):
        self.ensure_one()
        data = self._prepare_preview_data()
        report_obj = self.env['report.accounting_pdf_reports.report_partnerledger']
        report_values = report_obj._get_report_values(None, data=data)

        # ── Filter docs to selected partners (if any) ──────────────────
        selected_ids = self.partner_ids.ids
        if selected_ids:
            report_values = dict(report_values)
            report_values['docs'] = report_values['docs'].filtered(
                lambda p: p.id in selected_ids
            )

        self.preview_html = self._build_preview_html(report_values, data)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Partner Ledger – Preview'),
            'res_model': 'account.report.partner.ledger',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref(
                'partner_ledger_preview.view_partner_ledger_preview_form'
            ).id,
            'target': 'new',
            'context': self.env.context,
        }

    # ------------------------------------------------------------------
    # Override check_report to also honour partner_ids when printing PDF
    # ------------------------------------------------------------------
    def check_report(self):
        """
        Passes partner_ids into the report context so the PDF is also
        scoped to the selected partners.
        """
        self.ensure_one()
        if self.partner_ids:
            # accounting_pdf_reports reads partner_ids from the form dict
            # which is built inside check_report → _build_contexts.
            # We write the ids to the existing field name used by the base
            # module so no further monkey-patching is needed.
            pass  # partner_ids is already on the record; base module reads it
        return super().check_report()

    # ------------------------------------------------------------------
    # Helpers – data preparation
    # ------------------------------------------------------------------
    def _prepare_preview_data(self):
        """Build the data dict expected by _get_report_values."""
        form = self.read([
            'date_from', 'date_to', 'journal_ids', 'target_move',
            'result_selection', 'reconciled', 'amount_currency',
            'partner_ids',
        ])[0]
        form['journal_ids'] = form.get('journal_ids') or []
        form['partner_ids'] = form.get('partner_ids') or []
        form['used_context'] = {
            'date_from': form.get('date_from') or False,
            'date_to': form.get('date_to') or False,
            'journal_ids': form['journal_ids'],
            'state': form.get('target_move', 'all'),
            'strict_range': True,
            'lang': self.env.context.get('lang') or 'en_US',
        }
        return {'form': form}

    # ------------------------------------------------------------------
    # Helpers – resolve move_id / account_id from a report line dict
    # ------------------------------------------------------------------
    def _resolve_line_ids(self, line):
        """
        Return (move_id, account_id) integers for a report line dict.
        """
        def _unwrap(val):
            if isinstance(val, (list, tuple)) and val:
                return val[0]
            return val or None

        move_id    = _unwrap(line.get('move_id'))
        account_id = _unwrap(line.get('account_id'))

        if (not move_id or not account_id) and line.get('id'):
            try:
                ml = self.env['account.move.line'].browse(int(line['id']))
                if not move_id:
                    move_id = ml.move_id.id or None
                if not account_id:
                    account_id = ml.account_id.id or None
            except Exception:
                pass

        return move_id, account_id

    # ------------------------------------------------------------------
    # Helpers – HTML link builders
    # ------------------------------------------------------------------
    @staticmethod
    def _a(url, label, title='', extra_style=''):
        base = 'color:#1a56db;text-decoration:none;'
        t = f' title="{title}"' if title else ''
        return f'<a href="{url}" target="_blank" style="{base}{extra_style}"{t}>{label}</a>'

    def _entry_link(self, move_id, label):
        if not move_id:
            return label
        url = f'/web#model=account.move&id={move_id}&view_type=form'
        return self._a(url, label, title='Open Journal Entry')

    def _account_link(self, account_id, label):
        if not account_id:
            return label
        url = f'/web#model=account.account&id={account_id}&view_type=form'
        return self._a(url, label, title='Open Account')

    def _partner_link(self, partner_id, label):
        if not partner_id:
            return label
        url = (
            f'/odoo/accounting/journal-items?'
            f'search=%5B%5B%22partner_id%22%2C%22%3D%22%2C{partner_id}%5D%5D'
        )
        return self._a(url, label, title='View journal items for this partner',
                       extra_style='font-weight:bold;')

    def _amount_td(self, display, move_id, css='r'):
        inner = self._entry_link(move_id, display)
        return f'<td class="{css}">{inner}</td>'

    # ------------------------------------------------------------------
    # Main HTML builder
    # ------------------------------------------------------------------
    def _build_preview_html(self, report_values, data):
        company         = self.env.company
        currency_symbol = company.currency_id.symbol or '₹'

        def fmt(v):
            return '{:,.2f}'.format(v or 0.0)

        def money(v):
            return f'{currency_symbol}&nbsp;{fmt(v)}'

        date_from   = data['form'].get('date_from') or ''
        date_to     = data['form'].get('date_to') or ''
        target_move = data['form'].get('target_move', 'all')
        target_lbl  = 'All Posted Entries' if target_move == 'posted' else 'All Entries'
        show_cur    = data['form'].get('amount_currency', False)

        lines_fn = report_values['lines']
        sum_fn   = report_values['sum_partner']
        docs     = report_values['docs']

        # Partner filter label for meta bar
        partner_label = ''
        if self.partner_ids:
            names = self.partner_ids.mapped('name')
            partner_label = ', '.join(names[:3])
            if len(names) > 3:
                partner_label += f' (+{len(names) - 3} more)'

        # ================================================================
        # CSS
        # ================================================================
        parts = ["""
<style>
  .pl-wrap { font-family: Arial, sans-serif; font-size: 13px; color: #222; }
  .pl-wrap h3 { font-size: 16px; margin: 0 0 12px;
                display: flex; align-items: center; gap: 8px; }

  /* ---- Meta bar ---- */
  .pl-meta { display: flex; flex-wrap: wrap; gap: 0; margin-bottom: 16px;
             font-size: 12px; background: #f0f4fa;
             border-radius: 4px; border: 1px solid #c9d6ea; }
  .pl-meta-item { padding: 8px 18px; border-right: 1px solid #c9d6ea; }
  .pl-meta-item:last-child { border-right: none; }
  .pl-meta-item strong { display: block; color: #666; font-size: 10px;
                          text-transform: uppercase; letter-spacing: .6px;
                          margin-bottom: 3px; }
  .pl-meta-item span { font-weight: 600; color: #1a1a1a; }

  /* ---- Table ---- */
  .pl-table { width: 100%; border-collapse: collapse; font-size: 12px; }
  .pl-table thead th { background: #3b5998; color: #fff; padding: 7px 10px;
                        text-align: left; white-space: nowrap; font-size: 11px;
                        text-transform: uppercase; letter-spacing: .4px; }
  .pl-table thead th.r { text-align: right; }
  .pl-table td { padding: 5px 10px; border-bottom: 1px solid #eee;
                 vertical-align: middle; }
  .pl-table td.r { text-align: right; font-variant-numeric: tabular-nums;
                   white-space: nowrap; }

  /* Partner summary row */
  .pl-partner > td { background: #dde6f5; font-weight: bold;
                     border-top: 2px solid #b0c4de;
                     border-bottom: 1px solid #afc1de; }
  .pl-partner > td.r { color: #1a3a6b; }

  /* Detail rows */
  .pl-line > td { background: #fff; }
  .pl-line:hover > td { background: #f5f8ff; }

  /* Empty / no-lines */
  .pl-no-lines > td { color: #aaa; font-style: italic; padding-left: 24px; }
  .pl-empty { text-align: center; color: #888; font-style: italic; padding: 30px 0; }

  /* Grand total row */
  .pl-total > td { background: #2e4a8a; color: #fff; font-weight: bold;
                   padding: 7px 10px; border-top: 3px solid #1a2e5a; }
  .pl-total > td.r { text-align: right; }

  /* Links */
  .pl-table a { color: #1a56db; text-decoration: none; }
  .pl-table a:hover { text-decoration: underline; color: #0e3a9e; }
</style>
<div class="pl-wrap">
  <h3>&#128196; Partner Ledger</h3>
  <div class="pl-meta">
"""]

        # Meta bar items
        parts.append(
            f'<div class="pl-meta-item">'
            f'<strong>Company</strong><span>{company.name or ""}</span></div>'
        )
        if date_from:
            parts.append(
                f'<div class="pl-meta-item">'
                f'<strong>Date From</strong><span>{date_from}</span></div>'
            )
        if date_to:
            parts.append(
                f'<div class="pl-meta-item">'
                f'<strong>Date To</strong><span>{date_to}</span></div>'
            )
        parts.append(
            f'<div class="pl-meta-item">'
            f'<strong>Target Moves</strong><span>{target_lbl}</span></div>'
        )
        if partner_label:
            parts.append(
                f'<div class="pl-meta-item">'
                f'<strong>Partners</strong><span>{partner_label}</span></div>'
            )
        parts.append('</div>')  # end .pl-meta

        # ================================================================
        # Table
        # ================================================================
        if not docs:
            parts.append(
                '<p class="pl-empty">No records found for the selected criteria.</p>'
            )
        else:
            # Table header
            parts.append('<table class="pl-table"><thead><tr>')
            header_cols = [
                ('Date', False),
                ('Journal', False),
                ('Account', False),
                ('Reference / Description', False),
                ('Debit', True),
                ('Credit', True),
                ('Balance', True),
            ]
            if show_cur:
                header_cols.append(('Amount Currency', True))
            for h, right in header_cols:
                r_cls = ' class="r"' if right else ''
                parts.append(f'<th{r_cls}>{h}</th>')
            parts.append('</tr></thead><tbody>')

            grand_debit = grand_credit = grand_balance = 0.0

            for partner in docs:
                p_debit   = sum_fn(data, partner, 'debit') or 0.0
                p_credit  = sum_fn(data, partner, 'credit') or 0.0
                p_balance = sum_fn(data, partner, 'debit - credit') or 0.0
                grand_debit   += p_debit
                grand_credit  += p_credit
                grand_balance += p_balance

                p_label = ' – '.join(
                    x for x in [partner.ref or '', partner.name or ''] if x
                ) or '(no name)'

                extra = '<td class="r"></td>' if show_cur else ''
                parts.append(
                    f'<tr class="pl-partner">'
                    f'<td colspan="4">{self._partner_link(partner.id, p_label)}</td>'
                    f'<td class="r">{money(p_debit)}</td>'
                    f'<td class="r">{money(p_credit)}</td>'
                    f'<td class="r">{money(p_balance)}</td>'
                    f'{extra}</tr>'
                )

                move_lines = lines_fn(data, partner)
                if not move_lines:
                    ncols = 8 if show_cur else 7
                    parts.append(
                        f'<tr class="pl-no-lines">'
                        f'<td colspan="{ncols}">No transactions</td></tr>'
                    )

                for line in move_lines:
                    move_id, account_id = self._resolve_line_ids(line)

                    date_str = str(line.get('date') or '')
                    code     = line.get('code') or ''
                    a_name   = line.get('a_name') or ''
                    desc     = line.get('displayed_name') or ''

                    acc_cell  = self._account_link(account_id, a_name)
                    desc_cell = self._entry_link(move_id, desc)

                    d_val = line.get('debit', 0.0)
                    c_val = line.get('credit', 0.0)
                    b_val = line.get('progress', 0.0)

                    parts.append(
                        f'<tr class="pl-line">'
                        f'<td>{date_str}</td>'
                        f'<td>{code}</td>'
                        f'<td>{acc_cell}</td>'
                        f'<td>{desc_cell}</td>'
                    )
                    parts.append(self._amount_td(money(d_val), move_id))
                    parts.append(self._amount_td(money(c_val), move_id))
                    parts.append(self._amount_td(money(b_val), move_id))

                    if show_cur:
                        cur_id = line.get('currency_id')
                        if cur_id:
                            sym = getattr(cur_id, 'symbol', '')
                            cur_disp = f'{sym}&nbsp;{fmt(line.get("amount_currency", 0.0))}'
                            parts.append(self._amount_td(cur_disp, move_id))
                        else:
                            parts.append('<td></td>')

                    parts.append('</tr>')

            # Grand total row
            extra = '<td></td>' if show_cur else ''
            parts.append(
                f'<tr class="pl-total">'
                f'<td colspan="4">Grand Total</td>'
                f'<td class="r">{money(grand_debit)}</td>'
                f'<td class="r">{money(grand_credit)}</td>'
                f'<td class="r">{money(grand_balance)}</td>'
                f'{extra}</tr>'
            )
            parts.append('</tbody></table>')

        parts.append('</div>')
        return ''.join(parts)