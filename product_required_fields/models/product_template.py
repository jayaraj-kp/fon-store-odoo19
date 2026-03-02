from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Override fields to make them required at model level (handles UI asterisk)
    default_code = fields.Char(required=True)
    barcode = fields.Char(required=True)
