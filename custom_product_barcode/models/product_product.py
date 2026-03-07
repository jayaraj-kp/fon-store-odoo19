# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    barcode2 = fields.Char(related='product_tmpl_id.barcode2', store=True, readonly=False)
    custom_qty1 = fields.Float(related='product_tmpl_id.custom_qty1', store=True, readonly=False, digits='Product Unit of Measure')
    custom_price1 = fields.Float(related='product_tmpl_id.custom_price1', store=True, readonly=False, digits='Product Price')

    barcode3 = fields.Char(related='product_tmpl_id.barcode3', store=True, readonly=False)
    custom_qty2 = fields.Float(related='product_tmpl_id.custom_qty2', store=True, readonly=False, digits='Product Unit of Measure')
    custom_price2 = fields.Float(related='product_tmpl_id.custom_price2', store=True, readonly=False, digits='Product Price')
