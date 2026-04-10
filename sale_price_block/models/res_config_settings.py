from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    block_sale_below_cost = fields.Boolean(
        string='Block Sale Below Cost Price',
        config_parameter='sale_price_block.block_below_cost',
        default=True,
        help='If enabled, sale orders cannot be confirmed when any product '
             'unit price is below the product cost price (standard price).',
    )
