from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    temp_price_ids = fields.One2many(
        'product.temp.price', 'product_tmpl_id', string='Scheduled Prices')
