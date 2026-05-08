# -*- coding: utf-8 -*-
from odoo import models, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.depends('name', 'default_code')
    def _compute_display_name(self):
        """
        Override display_name to show only product name without internal reference code.
        This removes the [CODE] prefix from product display in POS.
        """
        for product in self:
            # Show only the product name without the internal reference code
            product.display_name = product.name


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.depends('name', 'default_code')
    def _compute_display_name(self):
        """
        Override display_name for product templates as well.
        """
        for product in self:
            # Show only the product name without the internal reference code
            product.display_name = product.name
