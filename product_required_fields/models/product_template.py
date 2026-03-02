from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Override fields to make them required at model level (handles UI asterisk)
    default_code = fields.Char(required=True)
    barcode = fields.Char(required=True)
    available_in_pos = fields.boolean(required=True)
    is_storable = fields.Boolean(required=True)
    categ_id = fields.many2one(required=True)
    image_1920 = fields.binary(required=True)