from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.constrains('default_code', 'barcode')
    def _check_required_reference_barcode(self):
        for record in self:
            missing = []
            if not record.default_code:
                missing.append(_('Reference'))
            if not record.barcode:
                missing.append(_('Barcode'))
            if missing:
                raise ValidationError(
                    _('The following required fields are missing: %s\n'
                      'Please fill in all required fields before saving.')
                    % ', '.join(missing)
                )
