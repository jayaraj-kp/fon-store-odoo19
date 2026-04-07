# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    block_sale_below_cost = fields.Boolean(
        string='Block Sales Below Cost Price',
        config_parameter='sale_cost_price_block.block_sale_below_cost',
        help='If enabled, sales orders and POS orders cannot be confirmed '
             'when any product line has a unit price below the product cost price.',
    )
    allow_manager_override = fields.Boolean(
        string='Allow Sales Manager to Override',
        config_parameter='sale_cost_price_block.allow_manager_override',
        help='If enabled, users with the Sales Manager role can bypass '
             'the cost price restriction.',
    )
