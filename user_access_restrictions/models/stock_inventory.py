# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.exceptions import AccessError


class StockQuant(models.Model):
    """Restrict Physical Inventory Adjustment access."""
    _inherit = 'stock.quant'

    def action_client_action(self):
        if self.env.user.restrict_physical_inventory:
            raise AccessError(
                "You do not have permission to access Physical Inventory Adjustment. "
                "Please contact your administrator."
            )
        return super().action_client_action()

    @api.model
    def _get_inventory_fields_write(self):
        """Block inventory adjustment writes for restricted users."""
        if self.env.user.restrict_physical_inventory:
            raise AccessError(
                "You do not have permission to adjust inventory. "
                "Please contact your administrator."
            )
        return super()._get_inventory_fields_write()
