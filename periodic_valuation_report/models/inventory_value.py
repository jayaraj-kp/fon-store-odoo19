from odoo import models, fields, api

class PeriodicValuation(models.TransientModel):
    _name = 'periodic.valuation.wizard'
    _description = 'Manual Inventory Valuation Report'

    @api.model
    def get_inventory_data(self):
        # Fetch all products that have stock
        products = self.env['product.product'].search([('type', '=', 'product')])
        data = []
        for p in products:
            if p.qty_available > 0:
                # Use current standard_price as the base cost
                data.append({
                    'name': p.name,
                    'qty': p.qty_available,
                    'price': p.standard_price,
                    'total': p.qty_available * p.standard_price
                })
        return data