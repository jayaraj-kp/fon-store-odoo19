# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    wh_stock_picking_id = fields.Many2one(
        'stock.picking',
        string='Internal Transfer',
        copy=False,
        readonly=True,
        index=True,
        help='Cross-warehouse internal transfer linked to this journal entry.',
    )
