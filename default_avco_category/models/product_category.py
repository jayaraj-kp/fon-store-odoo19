# -*- coding: utf-8 -*-
from odoo import models, fields


class ProductCategory(models.Model):
    """
    Inherits product.category (defined in stock/product_category.py) and
    overrides the default value of `cost_method` so that every new category
    is pre-filled with 'average_price' (AVCO) instead of 'standard'.
    """
    _inherit = 'product.category'

    # Override the field to change only its default; everything else is kept.
    cost_method = fields.Selection(
        default='average_price',   # 'standard' | 'average_price' | 'fifo'
    )
