from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    model_number = fields.Char(
        string='Model',
        size=255,
        tracking=True,
        help='Alphanumeric model number/identifier for the product'
    )


class ProductProduct(models.Model):
    _inherit = 'product.product'

    model_number = fields.Char(
        string='Model',
        size=255,
        tracking=True,
        help='Alphanumeric model number/identifier for the product'
    )