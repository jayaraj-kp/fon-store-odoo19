# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.exceptions import AccessError


class StockQuant(models.Model):
    """Restrict Physical Inventory Adjustment (stock.quant) access."""
    _inherit = 'stock.quant'

    def write(self, vals):
        # Block inventory quantity adjustments
        if self.env.user.restrict_physical_inventory:
            inventory_fields = {'inventory_quantity', 'inventory_quantity_auto_apply'}
            if inventory_fields.intersection(vals.keys()):
                raise AccessError(
                    "Access Denied: You do not have permission to adjust inventory quantities.\n"
                    "Please contact your administrator."
                )
        return super().write(vals)

    def action_apply_inventory(self):
        if self.env.user.restrict_physical_inventory:
            raise AccessError(
                "Access Denied: You do not have permission to apply inventory adjustments.\n"
                "Please contact your administrator."
            )
        return super().action_apply_inventory()
