from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    rack = fields.Char(
        string='Rack',
        help='Rack / shelf location for this order line item.',
    )
