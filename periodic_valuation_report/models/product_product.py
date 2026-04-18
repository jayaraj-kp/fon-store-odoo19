from odoo import models, fields, api

class ProductProduct(models.Model):
    _inherit = 'product.product'

    # This creates a 'virtual' field that Odoo can now display
    total_inventory_value = fields.Float(
        string="Total Value",
        compute="_compute_total_inventory_value"
    )

    @api.depends('qty_available', 'standard_price')
    def _compute_total_inventory_value(self):
        for product in self:
            product.total_inventory_value = product.qty_available * product.standard_price