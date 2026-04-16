# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockValuationLayerCE(models.Model):
    """
    Extends stock.valuation.layer with a computed journal-entry link.
    stock.valuation.layer is defined in stock_account which is a hard
    dependency – Odoo will install it before loading this module.
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
        if 'account.move' not in self.env:
            for rec in self:
                rec.account_move_id = False
            return
        for rec in self:
            rec.account_move_id = (
                self.env['account.move'].search(
                    [('stock_move_id', '=', rec.stock_move_id.id)], limit=1
                ) if rec.stock_move_id else False
            )


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
        return {
            'type': 'ir.actions.act_window',
            'name': 'Stock Valuation at %s' % fields.Datetime.to_string(self.date),
            'res_model': 'stock.valuation.layer',
            'view_mode': 'list,pivot,graph',
            'domain': domain,
            'context': {'valuation_date': fields.Datetime.to_string(self.date)},
        }
