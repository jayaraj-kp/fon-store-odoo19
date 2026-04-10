# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CostPriceProtectionWizard(models.TransientModel):
    """
    Dedicated settings wizard for Cost Price Protection.
    Reads/writes ir.config_parameter directly.
    No res.config.settings inheritance = no XPath issues.
    """
    _name = 'cost.price.protection.wizard'
    _description = 'Cost Price Protection Settings'

    block_sale_below_cost = fields.Boolean(
        string='Block Sales Below Cost Price',
        help='Block sales orders and POS orders when any product line '
             'is priced below the product cost price.',
    )
    allow_manager_override = fields.Boolean(
        string='Allow Sales Manager Override',
        help='Sales Managers can confirm orders even if priced below cost.',
    )

    @api.model
    def default_get(self, fields_list):
        """Load current values from ir.config_parameter."""
        res = super().default_get(fields_list)
        ICP = self.env['ir.config_parameter'].sudo()
        res['block_sale_below_cost'] = ICP.get_param(
            'sale_cost_price_block.block_sale_below_cost', False) in (True, 'True', '1', 'true')
        res['allow_manager_override'] = ICP.get_param(
            'sale_cost_price_block.allow_manager_override', False) in (True, 'True', '1', 'true')
        return res

    def action_save(self):
        """Save values to ir.config_parameter and close."""
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('sale_cost_price_block.block_sale_below_cost',
                      str(self.block_sale_below_cost))
        ICP.set_param('sale_cost_price_block.allow_manager_override',
                      str(self.allow_manager_override))
        return {'type': 'ir.actions.act_window_close'}
