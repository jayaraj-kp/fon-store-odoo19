# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.exceptions import AccessError


class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.user.restrict_scrap_menu:
            raise AccessError(
                "Access Denied: You do not have permission to create scrap orders.\n"
                "Please contact your administrator."
            )
        return super().create(vals_list)

    def write(self, vals):
        if self.env.user.restrict_scrap_menu:
            raise AccessError(
                "Access Denied: You do not have permission to modify scrap orders.\n"
                "Please contact your administrator."
            )
        return super().write(vals)

    def action_validate(self):
        if self.env.user.restrict_scrap_menu:
            raise AccessError(
                "Access Denied: You do not have permission to validate scrap orders.\n"
                "Please contact your administrator."
            )
        return super().action_validate()
