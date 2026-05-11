from odoo import api, models, fields
# ... existing imports ...

class ProductProduct(models.Model):
    _inherit = 'product.product'

    # ... existing fields ...

    @api.model
    def _load_pos_data_fields(self, config):
        fields = super()._load_pos_data_fields(config)
        if 'mrp_price' not in fields:
            fields.append('mrp_price')
        return fields