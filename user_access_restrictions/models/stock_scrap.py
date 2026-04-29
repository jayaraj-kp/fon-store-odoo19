# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.exceptions import AccessError


class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    @api.model
    def create(self, vals):
        if self.env.user.restrict_scrap_menu:
            raise AccessError(
                "You do not have permission to create scrap orders. "
                "Please contact your administrator."
            )
        return super().create(vals)

    def write(self, vals):
        if self.env.user.restrict_scrap_menu:
            raise AccessError(
                "You do not have permission to modify scrap orders. "
                "Please contact your administrator."
            )
        return super().write(vals)
