from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    warranty_months = fields.Integer(
        string="Warranty (Months)",
        default=0,
        help="Number of months of warranty coverage starting from the date "
             "an individual unit (serial number) is sold to a customer. "
             "Set to 0 if this product has no warranty.",
    )
