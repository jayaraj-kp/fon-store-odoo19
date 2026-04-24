# periodic_valuation_report/models/product_product.py
from odoo import models, fields, api

class ProductProduct(models.Model):
    _inherit = 'product.product'

    # In product_product.py
    total_inventory_value = fields.Float(
        string="Custom Total Value",  # Change this label!
        compute="_compute_total_inventory_value",
        store=False
    )

    @api.depends('qty_available', 'standard_price')
    def _compute_total_inventory_value(self):
        for product in self:
            # Add this line to test if the method is hit
            print(f"DEBUG: Computing value for {product.name}")
            product.total_inventory_value = product.qty_available * product.standard_price