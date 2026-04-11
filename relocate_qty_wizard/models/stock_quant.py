# -*- coding: utf-8 -*-
from odoo import models


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def action_relocate_quants(self):
        """
        Override the standard Relocate action to open our custom wizard
        that includes a product/quantity adjustment table.
        """
        return {
            'name': 'Relocate Stock Quant',
            'type': 'ir.actions.act_window',
            'res_model': 'relocate.qty.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_quant_ids': self.ids,
            },
        }
