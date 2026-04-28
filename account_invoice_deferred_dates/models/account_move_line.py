# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    deferred_start_date = fields.Date(
        string='Start Date',
        help='Start date for deferred expense/revenue recognition.',
        copy=True,
    )

    deferred_end_date = fields.Date(
        string='End Date',
        help='End date for deferred expense/revenue recognition.',
        copy=True,
    )

    deferred_account_id = fields.Many2one(
        'account.account',
        string='Deferred Account',
        help='Balance sheet account to park the deferred amount (e.g. Prepaid Expense / Unearned Revenue).',
        copy=True,
        domain="[('account_type', 'not in', ['income', 'income_other', 'expense', 'expense_depreciation', 'expense_direct_cost'])]",
    )

    @api.constrains('deferred_start_date', 'deferred_end_date')
    def _check_deferred_dates(self):
        for line in self:
            if (
                line.deferred_start_date
                and line.deferred_end_date
                and line.deferred_start_date > line.deferred_end_date
            ):
                raise ValidationError(
                    "Deferred End Date must be greater than or equal to "
                    "Deferred Start Date on line: '%s'"
                    % (line.name or (line.product_id.name if line.product_id else '') or line.account_id.name or '')
                )
