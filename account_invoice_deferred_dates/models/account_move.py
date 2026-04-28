# -*- coding: utf-8 -*-
import calendar
from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    deferred_move_ids = fields.Many2many(
        'account.move',
        'account_move_deferred_rel',
        'origin_move_id',
        'deferred_move_id',
        string='Deferred Journal Entries',
        copy=False,
    )

    deferred_move_count = fields.Integer(
        string='Deferred Entries Count',
        compute='_compute_deferred_move_count',
    )

    @api.depends('deferred_move_ids')
    def _compute_deferred_move_count(self):
        for move in self:
            move.deferred_move_count = len(move.deferred_move_ids)

    # ------------------------------------------------------------------
    # Override action_post to auto-generate deferred entries on confirm
    # ------------------------------------------------------------------
    def action_post(self):
        res = super().action_post()
        for move in self:
            if move.move_type in ('in_invoice', 'out_invoice', 'in_refund', 'out_refund'):
                move._generate_deferred_entries()
        return res

    def _generate_deferred_entries(self):
        """Generate monthly equal deferred journal entries for lines that
        have deferred_start_date, deferred_end_date and deferred_account_id."""
        self.ensure_one()
        deferred_lines = self.invoice_line_ids.filtered(
            lambda l: l.deferred_start_date
            and l.deferred_end_date
            and l.deferred_account_id
            and l.deferred_start_date <= l.deferred_end_date
        )
        if not deferred_lines:
            return

        # Remove any previously generated deferred entries for this move
        old_entries = self.deferred_move_ids.filtered(lambda m: m.state == 'draft')
        if old_entries:
            old_entries.unlink()

        # Find or create a Miscellaneous journal
        misc_journal = self.env['account.journal'].search(
            [('type', '=', 'general'), ('company_id', '=', self.company_id.id)],
            limit=1,
        )
        if not misc_journal:
            raise UserError(_(
                "No General (Miscellaneous) journal found. "
                "Please create one in Accounting > Configuration > Journals."
            ))

        new_moves = self.env['account.move']

        for line in deferred_lines:
            monthly_periods = self._get_monthly_periods(
                line.deferred_start_date, line.deferred_end_date
            )
            if not monthly_periods:
                continue

            total_amount = abs(line.price_subtotal)
            n = len(monthly_periods)
            base_amount = round(total_amount / n, 2)
            # Put any rounding remainder on the last period
            last_amount = round(total_amount - base_amount * (n - 1), 2)

            # Determine debit/credit sides depending on move type
            # For vendor bills (expense): debit deferred_account (asset), credit expense account
            # For customer invoices (revenue): debit revenue account, credit deferred_account (liability)
            is_expense = self.move_type in ('in_invoice', 'in_refund')

            for idx, (period_date, _label) in enumerate(monthly_periods):
                amount = last_amount if idx == n - 1 else base_amount
                if amount == 0:
                    continue

                label = _("Deferral of %s") % self.name

                if is_expense:
                    # Debit: Prepaid/Deferred Account (reduce the prepaid)
                    # Credit: Expense Account (recognize the expense)
                    move_lines = [
                        (0, 0, {
                            'account_id': line.deferred_account_id.id,
                            'name': label,
                            'debit': 0.0,
                            'credit': amount,
                        }),
                        (0, 0, {
                            'account_id': line.account_id.id,
                            'name': label,
                            'debit': amount,
                            'credit': 0.0,
                        }),
                    ]
                else:
                    # Revenue deferral
                    # Debit: Revenue account (reduce unearned)
                    # Credit: Deferred/Liability account (recognize revenue)
                    move_lines = [
                        (0, 0, {
                            'account_id': line.deferred_account_id.id,
                            'name': label,
                            'debit': amount,
                            'credit': 0.0,
                        }),
                        (0, 0, {
                            'account_id': line.account_id.id,
                            'name': label,
                            'debit': 0.0,
                            'credit': amount,
                        }),
                    ]

                deferred_move = self.env['account.move'].create({
                    'move_type': 'entry',
                    'journal_id': misc_journal.id,
                    'date': period_date,
                    'ref': label,
                    'company_id': self.company_id.id,
                    'line_ids': move_lines,
                })
                new_moves |= deferred_move

        if new_moves:
            self.deferred_move_ids = [(4, m.id) for m in new_moves]

    def _get_monthly_periods(self, start_date, end_date):
        """Return list of (last_day_of_month, label) tuples between start and end dates."""
        periods = []
        current = start_date.replace(day=1)
        end_month_start = end_date.replace(day=1)

        while current <= end_month_start:
            last_day = current.replace(
                day=calendar.monthrange(current.year, current.month)[1]
            )
            # Cap the last period to end_date if end_date < last day of month
            period_end = min(last_day, end_date)
            label = current.strftime('%B %Y')
            periods.append((period_end, label))
            current = current + relativedelta(months=1)

        return periods

    # ------------------------------------------------------------------
    # Smart button action
    # ------------------------------------------------------------------
    def action_view_deferred_entries(self):
        self.ensure_one()
        return {
            'name': _('Deferred Entries'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.deferred_move_ids.ids)],
            'context': {
                'default_move_type': 'entry',
                'create': False,
            },
        }

    # ------------------------------------------------------------------
    # When bill is reset to draft, remove generated deferred entries
    # ------------------------------------------------------------------
    def button_draft(self):
        res = super().button_draft()
        for move in self:
            draft_deferred = move.deferred_move_ids.filtered(
                lambda m: m.state == 'draft'
            )
            if draft_deferred:
                draft_deferred.unlink()
        return res
