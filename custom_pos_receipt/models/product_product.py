from odoo import models

class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _load_pos_data_fields(self, config_id):
        fields = super()._load_pos_data_fields(config_id)
        if 'mrp_price' not in fields:
            fields.append('mrp_price')
        return fields