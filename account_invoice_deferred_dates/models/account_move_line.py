# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    deferred_start_date = fields.Date(
        string='Start Date',
        help='Start date for deferred revenue/expense recognition.',
        copy=True,
    )

    deferred_end_date = fields.Date(
        string='End Date',
        help='End date for deferred revenue/expense recognition.',
        copy=True,
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
                    "Deferred Start Date on line: %s" % (line.name or line.product_id.name or '')
                )
