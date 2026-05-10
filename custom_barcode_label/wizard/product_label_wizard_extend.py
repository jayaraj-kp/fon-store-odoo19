# -*- coding: utf-8 -*-
from odoo import models, fields


class ProductLabelWizardExtend(models.TransientModel):
    """Extend the built-in Product Label Wizard to rename 'Show MRP' → 'Show Sales Price'."""
    _inherit = 'product.label.wizard'

    # Override the field just to change its string/label.
    # The field already exists on the parent model; we only change the display name.
    show_mrp = fields.Boolean(string='Show Sales Price')