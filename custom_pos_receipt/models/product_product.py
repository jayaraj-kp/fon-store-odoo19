from odoo import models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _load_pos_data_fields(self, config_id):
        fields = super()._load_pos_data_fields(config_id)
        if 'mrp_price' not in fields:
            fields.append('mrp_price')
        return fields


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _load_pos_data_fields(self, config_id):
        fields = super()._load_pos_data_fields(config_id)
        if 'mrp_price' not in fields:
            fields.append('mrp_price')
        return fields