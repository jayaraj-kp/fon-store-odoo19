from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Override fields to make them required at model level (handles UI + API)
    default_code = fields.Char(required=True)
    barcode = fields.Char(required=True)

    @api.constrains('default_code', 'barcode')
    def _check_required_reference_barcode(self):
        for record in self:
            missing = []
            if not record.default_code:
                missing.append(_('Reference (Internal Reference)'))
            if not record.barcode:
                missing.append(_('Barcode'))
            if missing:
                raise ValidationError(
                    _('The following required fields are missing: %s\n'
                      'Please fill in all required fields before saving.')
                    % ', '.join(missing)
                )


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # Also enforce on product.product (variant level)
    barcode = fields.Char(required=True)
    default_code = fields.Char(required=True)
