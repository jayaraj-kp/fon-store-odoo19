from odoo import fields, models, api, _
from datetime import timedelta


class AccountDayBookReport(models.TransientModel):
    _name = "account.daybook.report"
    _description = "Day Book Report"

    date_from = fields.Date(string='Start Date', default=fields.Date.context_today, required=True)
    date_to = fields.Date(string='End Date', default=fields.Date.context_today, required=True)
    target_move = fields.Selection([('posted', 'Posted Entries'),
                                    ('all', 'All Entries')], string='Target Moves', required=True,
                                   default='posted')
    journal_ids = fields.Many2many('account.journal', string='Journals', required=True,
                                   default=lambda self: self.env['account.journal'].search([]))
    account_ids = fields.Many2many('account.account', 'account_account_daybook_report', 'report_line_id',
                                   'account_id', 'Accounts')

    preview_html = fields.Html(
        string='Preview',
        sanitize=False,
        readonly=True,
    )

    def _build_comparison_context(self, data):
        result = {}
        result['journal_ids'] = 'journal_ids' in data['form'] and data['form']['journal_ids'] or False
        result['state'] = 'target_move' in data['form'] and data['form']['target_move'] or ''
        result['date_from'] = data['form']['date_from']
        result['date_to'] = data['form']['date_to']
        return result

    def check_report(self):
        data = {}
        data['form'] = self.read(['target_move', 'date_from', 'date_to', 'journal_ids', 'account_ids'])[0]
        comparison_context = self._build_comparison_context(data)
        data['form']['comparison_context'] = comparison_context
        return self.env.ref(
            'om_account_daily_reports.action_report_day_book').report_action(self,
                                                                     data=data)

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------
    def action_preview_report(self):
        self.ensure_one()
        data = {}
        data['form'] = self.read(['target_move', 'date_from', 'date_to', 'journal_ids', 'account_ids'])[0]
        comparison_context = self._build_comparison_context(data)
        data['form']['comparison_context'] = comparison_context

        # Get the report data directly
        report_obj = self.env['report.om_account_daily_reports.report_daybook']
        form_data = data['form']

        date_from = fields.Date.from_string(form_data['date_from'])
        date_to = fields.Date.from_string(form_data['date_to'])

        account_ids = form_data.get('account_ids', [])
        if account_ids:
            accounts = self.env['account.account'].browse(account_ids)
        else:
            accounts = self.env['account.account'].search([])

        dates = []
        days_total = date_to - date_from
        for day in range(days_total.days + 1):
            dates.append(date_from + timedelta(days=day))

        records = []
        for date in dates:
            date_data = str(date)
            accounts_res = report_obj._get_account_move_entry(accounts, form_data, date_data)
            if accounts_res['lines']:
                records.append({
                    'date': date,
                    'debit': accounts_res['debit'],
                    'credit': accounts_res['credit'],
                    'balance': accounts_res['balance'],
                    'move_lines': accounts_res['lines']
                })

        codes = []
        if data['form'].get('journal_ids', False):
            codes = [j.code for j in self.env['account.journal'].browse(data['form']['journal_ids'])]

        self.preview_html = self._build_preview_html(records, data, codes)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Day Book – Preview'),
            'res_model': 'account.daybook.report',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref(
                'om_account_daily_reports.view_daybook_preview_form'
            ).id,
            'target': 'new',
            'context': self.env.context,
        }

    # ------------------------------------------------------------------
    # HTML builder helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _a(url, label, title='', extra_style=''):
        base = 'color:#1a56db;text-decoration:none;'
        t = f' title="{title}"' if title else ''
        return f'<a href="{url}" target="_blank" style="{base}{extra_style}"{t}>{label}</a>'

    def _entry_link(self, move_name, label):
        if not move_name:
            return label
        move = self.env['account.move'].search([('name', '=', move_name)], limit=1)
        if not move:
            return label
        url = f'/web#model=account.move&id={move.id}&view_type=form'
        return self._a(url, label, title='Open Journal Entry')

    def _build_preview_html(self, records, data, codes):
        company = self.env.company
        currency_symbol = company.currency_id.symbol or ''

        def fmt(v):
            return '{:,.2f}'.format(v or 0.0)

        def money(v):
            return f'{currency_symbol}&nbsp;{fmt(v)}'

        form = data['form']
        date_from = form.get('date_from') or ''
        date_to = form.get('date_to') or ''
        target_move = form.get('target_move', 'all')
        target_lbl = 'Posted Entries' if target_move == 'posted' else 'All Entries'

        parts = ["""
<style>
  .dr-wrap { font-family: Arial, sans-serif; font-size: 13px; color: #222; }
  .dr-wrap h3 { font-size: 16px; margin: 0 0 12px;
                display: flex; align-items: center; gap: 8px; }
  .dr-meta { display: flex; flex-wrap: wrap; gap: 0; margin-bottom: 16px;
             font-size: 12px; background: #f0f4fa;
             border-radius: 4px; border: 1px solid #c9d6ea; }
  .dr-meta-item { padding: 8px 18px; border-right: 1px solid #c9d6ea; }
  .dr-meta-item:last-child { border-right: none; }
  .dr-meta-item strong { display: block; color: #666; font-size: 10px;
                          text-transform: uppercase; letter-spacing: .6px;
                          margin-bottom: 3px; }
  .dr-meta-item span { font-weight: 600; color: #1a1a1a; }
  .dr-table { width: 100%; border-collapse: collapse; font-size: 12px; }
  .dr-table thead th { background: #3b5998; color: #fff; padding: 7px 10px;
                        text-align: left; white-space: nowrap; font-size: 11px;
                        text-transform: uppercase; letter-spacing: .4px; }
  .dr-table thead th.r { text-align: right; }
  .dr-table td { padding: 5px 10px; border-bottom: 1px solid #eee;
                 vertical-align: middle; }
  .dr-table td.r { text-align: right; font-variant-numeric: tabular-nums;
                   white-space: nowrap; }
  .dr-date > td { background: #dde6f5; font-weight: bold;
                  border-top: 2px solid #b0c4de;
                  border-bottom: 1px solid #afc1de; }
  .dr-date > td.r { color: #1a3a6b; }
  .dr-line > td { background: #fff; }
  .dr-line:hover > td { background: #f5f8ff; }
  .dr-total > td { background: #2e4a8a; color: #fff; font-weight: bold;
                   padding: 7px 10px; border-top: 3px solid #1a2e5a; }
  .dr-total > td.r { text-align: right; }
  .dr-empty { text-align: center; color: #888; font-style: italic; padding: 30px 0; }
  .dr-table a { color: #1a56db; text-decoration: none; }
  .dr-table a:hover { text-decoration: underline; color: #0e3a9e; }
</style>
<div class="dr-wrap">
  <h3>&#128197; Day Book</h3>
  <div class="dr-meta">
"""]

        # Meta bar
        parts.append(
            f'<div class="dr-meta-item">'
            f'<strong>Company</strong><span>{company.name or ""}</span></div>'
        )
        parts.append(
            f'<div class="dr-meta-item">'
            f'<strong>Journals</strong><span>{", ".join(codes) or "All"}</span></div>'
        )
        if date_from:
            parts.append(
                f'<div class="dr-meta-item">'
                f'<strong>Date From</strong><span>{date_from}</span></div>'
            )
        if date_to:
            parts.append(
                f'<div class="dr-meta-item">'
                f'<strong>Date To</strong><span>{date_to}</span></div>'
            )
        parts.append(
            f'<div class="dr-meta-item">'
            f'<strong>Target Moves</strong><span>{target_lbl}</span></div>'
        )
        parts.append('</div>')  # end .dr-meta

        if not records:
            parts.append('<p class="dr-empty">No records found for the selected criteria.</p>')
        else:
            parts.append('<table class="dr-table"><thead><tr>')
            headers = [
                ('Date', False), ('JRNL', False), ('Partner', False),
                ('Ref', False), ('Move', False), ('Entry Label', False),
                ('Debit', True), ('Credit', True), ('Balance', True),
            ]
            for h, right in headers:
                r_cls = ' class="r"' if right else ''
                parts.append(f'<th{r_cls}>{h}</th>')
            parts.append('</tr></thead><tbody>')

            grand_debit = grand_credit = grand_balance = 0.0

            for day_record in records:
                d_date = day_record.get('date', '')
                d_debit = day_record.get('debit', 0.0)
                d_credit = day_record.get('credit', 0.0)
                d_balance = day_record.get('balance', 0.0)
                grand_debit += d_debit
                grand_credit += d_credit
                grand_balance += d_balance

                parts.append(
                    f'<tr class="dr-date">'
                    f'<td colspan="6">{d_date}</td>'
                    f'<td class="r">{money(d_debit)}</td>'
                    f'<td class="r">{money(d_credit)}</td>'
                    f'<td class="r">{money(d_balance)}</td>'
                    f'</tr>'
                )

                for line in day_record.get('move_lines', []):
                    ldate = line.get('ldate') or ''
                    lcode = line.get('lcode') or ''
                    partner = line.get('lpartner_id') or ''
                    lref = line.get('lref') or ''
                    move_name = line.get('move_name') or ''
                    lname = line.get('lname') or ''
                    d_val = line.get('debit', 0.0)
                    c_val = line.get('credit', 0.0)
                    b_val = line.get('balance', 0.0)

                    move_cell = self._entry_link(move_name, move_name) if move_name else ''

                    parts.append(
                        f'<tr class="dr-line">'
                        f'<td>{ldate}</td>'
                        f'<td>{lcode}</td>'
                        f'<td>{partner}</td>'
                        f'<td>{lref}</td>'
                        f'<td>{move_cell}</td>'
                        f'<td>{lname}</td>'
                        f'<td class="r">{money(d_val)}</td>'
                        f'<td class="r">{money(c_val)}</td>'
                        f'<td class="r">{money(b_val)}</td>'
                        f'</tr>'
                    )

            # Grand total
            parts.append(
                f'<tr class="dr-total">'
                f'<td colspan="6">Grand Total</td>'
                f'<td class="r">{money(grand_debit)}</td>'
                f'<td class="r">{money(grand_credit)}</td>'
                f'<td class="r">{money(grand_balance)}</td>'
                f'</tr>'
            )
            parts.append('</tbody></table>')

        parts.append('</div>')
        return ''.join(parts)
