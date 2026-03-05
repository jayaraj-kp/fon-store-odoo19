# -*- coding: utf-8 -*-
import random
import string
import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # -------------------------------------------------------------------------
    # Helper: reuse same logic as product.template
    # -------------------------------------------------------------------------
    def _generate_barcode(self):
        """Delegate barcode generation to product.template helper."""
        return self.env['product.template']._generate_barcode()

    # -------------------------------------------------------------------------
    # Override create: assign barcode to variants that don't have one
    # (applies when variants are created independently, e.g. via attributes)
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Only auto-assign if barcode is absent AND the template barcode
            # is not being set (multi-variant products need per-variant codes)
            if not vals.get('barcode'):
                barcode = self._generate_barcode()
                if barcode:
                    vals['barcode'] = barcode
        return super().create(vals_list)
