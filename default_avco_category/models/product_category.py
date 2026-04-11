# -*- coding: utf-8 -*-
from odoo import models, api


class ProductCategory(models.Model):
    """
    Inherits product.category and overrides default_get so that every new
    category form opens with 'average_price' (AVCO) pre-selected.
    """
    _inherit = 'product.category'

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        # Always force AVCO — overrides the hardcoded 'standard' set by parent
        if 'cost_method' in fields_list:
            defaults['cost_method'] = 'average_price'
        return defaults
