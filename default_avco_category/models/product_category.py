# -*- coding: utf-8 -*-
from odoo import models, api


class ProductCategory(models.Model):
    """
    Inherits product.category and overrides default_get so that every new
    category form opens with 'average_price' (AVCO) pre-selected.

    We use default_get instead of re-declaring the Selection field because
    Odoo 19 raises:
        AssertionError: Field product.category.cost_method without selection
    when a Selection field is overridden without repeating the full selection list.
    """
    _inherit = 'product.category'

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if 'cost_method' in fields_list and 'cost_method' not in defaults:
            defaults['cost_method'] = 'average_price'
        return defaults
