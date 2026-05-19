from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    rack = fields.Many2one(
        comodel_name='stock.location',
        string='Rack',
        domain=[('usage', '=', 'internal')],
        help='Internal stock location (rack/shelf) for this order line item.',
    )
