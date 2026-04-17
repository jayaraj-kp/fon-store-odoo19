from odoo import fields, models, api, _


class AccountPartnerLedgerPreview(models.TransientModel):
    """
    Inherits account.report.partner.ledger (from accounting_pdf_reports)
    and adds an inline HTML preview capability.
    No changes are made to the original module.
    """
    _inherit = 'account.report.partner.ledger'

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
    # Helpers
    # ------------------------------------------------------------------
    def _prepare_preview_data(self):
        """Build the data dict expected by _get_report_values."""
        form = self.read([
            'date_from', 'date_to', 'journal_ids', 'target_move',
            'result_selection', 'reconciled', 'amount_currency',
            'partner_ids',
        ])[0]
        # many2many fields arrive as lists of ids – keep them that way
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

    def _build_preview_html(self, report_values, data):
        """Return a fully self-contained HTML string for the preview widget."""
        company = self.env.company
        currency_symbol = company.currency_id.symbol or ''

        def fmt(value):
            return '{:,.2f}'.format(value or 0.0)

        date_from = data['form'].get('date_from') or ''
        date_to = data['form'].get('date_to') or ''
        target_move = data['form'].get('target_move', 'all')
        target_label = 'All Posted Entries' if target_move == 'posted' else 'All Entries'
        show_currency = data['form'].get('amount_currency', False)

        lines_fn = report_values['lines']
        sum_fn = report_values['sum_partner']
        docs = report_values['docs']

        # ---- CSS -------------------------------------------------------
        parts = ["""
<style>
  .pl-wrap { font-family: Arial, sans-serif; font-size: 13px; color: #222; }
  .pl-wrap h3 { font-size: 16px; margin: 0 0 8px; }
  .pl-meta { display: flex; flex-wrap: wrap; gap: 24px; margin-bottom: 14px;
             font-size: 12px; background: #f0f4fa; padding: 8px 12px;
             border-radius: 4px; }
  .pl-meta div strong { display: block; color: #555; font-size: 11px;
                        text-transform: uppercase; letter-spacing: .4px; }
  .pl-table { width: 100%; border-collapse: collapse; font-size: 12px; }
  .pl-table thead th { background: #3b5998; color: #fff; padding: 6px 8px;
                        text-align: left; white-space: nowrap; }
  .pl-table thead th.r { text-align: right; }
  .pl-table td { padding: 4px 8px; border-bottom: 1px solid #eee;
                 vertical-align: top; }
  .pl-table td.r { text-align: right; font-variant-numeric: tabular-nums;
                   white-space: nowrap; }
  .pl-partner td { background: #dde6f5; font-weight: bold; }
  .pl-no-lines td { color: #aaa; font-style: italic; padding-left: 24px; }
  .pl-empty { text-align: center; color: #888; font-style: italic;
              padding: 30px 0; }
</style>
<div class="pl-wrap">
  <h3>&#128196; Partner Ledger</h3>
  <div class="pl-meta">
"""]

        # meta bar
        parts.append(f'<div><strong>Company</strong>{company.name or ""}</div>')
        if date_from:
            parts.append(f'<div><strong>Date From</strong>{date_from}</div>')
        if date_to:
            parts.append(f'<div><strong>Date To</strong>{date_to}</div>')
        parts.append(f'<div><strong>Target Moves</strong>{target_label}</div>')
        parts.append('</div>')  # .pl-meta

        # ---- table -----------------------------------------------------
        if not docs:
            parts.append('<p class="pl-empty">No records found for the selected criteria.</p>')
        else:
            parts.append('<table class="pl-table"><thead><tr>')
            headers = ['Date', 'Journal', 'Account', 'Reference / Description',
                       'Debit', 'Credit', 'Balance']
            if show_currency:
                headers.append('Amount Currency')
            for h in headers:
                cls = ' class="r"' if h in ('Debit', 'Credit', 'Balance', 'Amount Currency') else ''
                parts.append(f'<th{cls}>{h}</th>')
            parts.append('</tr></thead><tbody>')

            for partner in docs:
                debit = sum_fn(data, partner, 'debit')
                credit = sum_fn(data, partner, 'credit')
                balance = sum_fn(data, partner, 'debit - credit')
                partner_label = ' – '.join(
                    p for p in [partner.ref or '', partner.name or ''] if p
                ) or '(no name)'

                extra_td = '<td></td>' if show_currency else ''
                parts.append(
                    f'<tr class="pl-partner">'
                    f'<td colspan="4">{partner_label}</td>'
                    f'<td class="r">{currency_symbol}&nbsp;{fmt(debit)}</td>'
                    f'<td class="r">{currency_symbol}&nbsp;{fmt(credit)}</td>'
                    f'<td class="r">{currency_symbol}&nbsp;{fmt(balance)}</td>'
                    f'{extra_td}'
                    f'</tr>'
                )

                move_lines = lines_fn(data, partner)
                if not move_lines:
                    cols = 8 if show_currency else 7
                    parts.append(
                        f'<tr class="pl-no-lines"><td colspan="{cols}">No transactions</td></tr>'
                    )
                for line in move_lines:
                    date_str = str(line.get('date') or '')
                    code = line.get('code') or ''
                    a_name = line.get('a_name') or ''
                    desc = line.get('displayed_name') or ''
                    row = (
                        f'<tr>'
                        f'<td>{date_str}</td>'
                        f'<td>{code}</td>'
                        f'<td>{a_name}</td>'
                        f'<td>{desc}</td>'
                        f'<td class="r">{currency_symbol}&nbsp;{fmt(line.get("debit", 0.0))}</td>'
                        f'<td class="r">{currency_symbol}&nbsp;{fmt(line.get("credit", 0.0))}</td>'
                        f'<td class="r">{currency_symbol}&nbsp;{fmt(line.get("progress", 0.0))}</td>'
                    )
                    if show_currency:
                        cur_id = line.get('currency_id')
                        if cur_id:
                            row += (
                                f'<td class="r">{cur_id.symbol}&nbsp;'
                                f'{fmt(line.get("amount_currency", 0.0))}</td>'
                            )
                        else:
                            row += '<td></td>'
                    row += '</tr>'
                    parts.append(row)

            parts.append('</tbody></table>')

        parts.append('</div>')
        return ''.join(parts)
