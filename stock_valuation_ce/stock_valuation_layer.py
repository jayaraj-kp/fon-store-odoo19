# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class StockValuationLayerCE(models.Model):
    """
    Extends stock.valuation.layer with a computed journal-entry link.

    stock.valuation.layer is defined in stock_account which is declared as a
    hard dependency in __manifest__.py.  Odoo guarantees it is loaded before
    this module, so _inherit is safe here.  The extra guard inside the compute
    method handles the edge case where account.move is absent (pure inventory
    install without accounting).
    """
    _inherit = 'stock.valuation.layer'

    account_move_id = fields.Many2one(
        comodel_name='account.move',
        string='Journal Entry',
        compute='_compute_account_move_id',
        store=False,
    )

    @api.depends('stock_move_id')
    def _compute_account_move_id(self):
        # Guard: account.move may not exist if accounting is not installed
        if 'account.move' not in self.env:
            for rec in self:
                rec.account_move_id = False
            return
        for rec in self:
            if rec.stock_move_id:
                rec.account_move_id = self.env['account.move'].search(
                    [('stock_move_id', '=', rec.stock_move_id.id)], limit=1
                )
            else:
                rec.account_move_id = False


class StockValuationAtDateCE(models.TransientModel):
    """
    Wizard – replicates the Enterprise 'Valuation at Date' button.
    """
    _name = 'stock.valuation.at.date.ce'
    _description = 'Stock Valuation at Date (CE)'

    date = fields.Datetime(
        string='Valuation Date',
        required=True,
        default=fields.Datetime.now,
    )
    product_ids = fields.Many2many(
        comodel_name='product.product',
        string='Products',
        help='Leave empty to include all products.',
    )
    location_id = fields.Many2one(
        comodel_name='stock.location',
        string='Location',
        domain=[('usage', '=', 'internal')],
        help='Leave empty for all internal locations.',
    )

    def action_show_valuation(self):
        self.ensure_one()
        domain = [('create_date', '<=', self.date)]
        if self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))
        if self.location_id:
            # Filter by warehouse/location via stock move origin
            domain.append(
                ('stock_move_id.location_dest_id', 'child_of', self.location_id.id)
            )
        return {
            'type': 'ir.actions.act_window',
            'name': 'Stock Valuation at %s' % fields.Datetime.to_string(self.date),
            'res_model': 'stock.valuation.layer',
            'view_mode': 'list,pivot,graph',
            'domain': domain,
            'context': {'valuation_date': fields.Datetime.to_string(self.date)},
        }
