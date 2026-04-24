# periodic_valuation_report/models/product_product.py
from odoo import models, fields, api

class ProductProduct(models.Model):
    _inherit = 'product.product'

    custom_inventory_value = fields.Float(
        string="Total Inventory Value",
        compute="_compute_custom_inventory_value",
        store=True,
        readonly=True
    )

    @api.depends('qty_available', 'standard_price')
    def _compute_custom_inventory_value(self):
        for product in self:
            product.custom_inventory_value = product.qty_available * product.standard_price