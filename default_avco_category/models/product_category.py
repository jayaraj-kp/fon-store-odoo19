# -*- coding: utf-8 -*-
from odoo import models, api


class ProductCategory(models.Model):
    """
    Overrides default_get for product.category.
    In Odoo 19 the costing method field is 'property_cost_method'
    with selection key 'average' for AVCO.
    Property fields ARE included in fields_list, but their default
    is set via ir.property — we force override after super().
    """
    _inherit = 'product.category'

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        # 'property_cost_method' is the real field; selection key is 'average'
        # We always overwrite whatever the parent/ir.property set
        defaults['property_cost_method'] = 'average'
        return defaults
