from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Override fields to make them required at model level (handles UI asterisk)
    # default_code = fields.Char(required=True)
    # barcode = fields.Char(required=True)
    available_in_pos = fields.Boolean(required=True, default=True)
    is_storable = fields.Boolean(required=True, default=True)
    categ_id = fields.Many2one(required=True)
    # image_1920 = fields.Binary(required=True)

    @api.model
    def default_get(self, fields_list):
        """
        Force default values for POS checkbox and Track Inventory checkbox.
        This method is more reliable than field-level defaults for
        inherited/computed fields in Odoo 17+.
        """
        defaults = super().default_get(fields_list)

        # Always enable "Point of Sale" checkbox by default
        if 'available_in_pos' in fields_list:
            defaults['available_in_pos'] = True

        # Always enable "Track Inventory" checkbox by default
        # In Odoo 17+, is_storable may be computed, so we set it here
        if 'is_storable' in fields_list:
            defaults['is_storable'] = True

        return defaults