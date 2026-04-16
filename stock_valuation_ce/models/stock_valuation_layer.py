# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools import float_round


class StockValuationLayerCE(models.Model):
    """
    Extends stock.valuation.layer to add CE-friendly reporting fields
    and the 'Valuation at Date' wizard helper.
    """
    _inherit = 'stock.valuation.layer'

    # --- Extra display fields ---
    remaining_qty = fields.Float(
        string='Remaining Qty',
        digits='Product Unit of Measure',
        help='Quantity still on hand from this valuation layer.',
    )
    unit_cost = fields.Float(
        string='Unit Value',
        digits='Product Price',
        help='Cost per unit for this valuation entry.',
    )
    remaining_value = fields.Float(
        string='Remaining Value',
        digits='Account',
        help='Value of the remaining quantity in this layer.',
    )

    # Convenient date alias used in the view
    create_date_display = fields.Datetime(
        string='Date',
        related='create_date',
        store=False,
    )

    # Link to journal entry (available when stock_account is installed)
    account_move_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        compute='_compute_account_move_id',
        store=False,
    )

    @api.depends('stock_move_id')
    def _compute_account_move_id(self):
        for rec in self:
            move = rec.stock_move_id
            if move:
                # Find the first account move linked to this stock move
                account_move = self.env['account.move'].search(
                    [('stock_move_id', '=', move.id)], limit=1
                )
                rec.account_move_id = account_move
            else:
                rec.account_move_id = False

    def action_open_journal_entry(self):
        self.ensure_one()
        if not self.account_move_id:
            return
        return {
            'type': 'ir.actions.act_window',
            'name': 'Journal Entry',
            'res_model': 'account.move',
            'res_id': self.account_move_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class StockValuationAtDateCE(models.TransientModel):
    """
    Wizard / helper that lets users filter the valuation report by a specific date.
    Mimics the Enterprise 'Valuation at Date' button behaviour.
    """
    _name = 'stock.valuation.at.date.ce'
    _description = 'Stock Valuation at Date (CE)'

    date = fields.Datetime(
        string='Valuation Date',
        required=True,
        default=fields.Datetime.now,
    )
    product_ids = fields.Many2many(
        'product.product',
        string='Products',
        help='Leave empty to include all products.',
    )
    location_id = fields.Many2one(
        'stock.location',
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
            'name': 'Stock Valuation at %s' % self.date,
            'res_model': 'stock.valuation.layer',
            'view_mode': 'list,pivot,graph',
            'domain': domain,
            'context': {
                'search_default_group_by_product': 0,
                'valuation_date': fields.Datetime.to_string(self.date),
            },
        }
