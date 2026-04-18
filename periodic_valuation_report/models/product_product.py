# periodic_valuation_report/models/product_product.py
from odoo import models, fields, api

class ProductProduct(models.Model):
    _inherit = 'product.product'

    total_inventory_value = fields.Float(
        string="Total Value",
        compute="_compute_total_inventory_value",
        store=False # Set to False so it doesn't try to look for a database column
    )

    @api.depends('qty_available', 'standard_price')
    def _compute_total_inventory_value(self):
        for product in self:
            product.total_inventory_value = product.qty_available * product.standard_price