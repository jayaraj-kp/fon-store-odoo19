# # -*- coding: utf-8 -*-
# import random
# import string
# import logging
#
# from odoo import api, fields, models, _
#
# _logger = logging.getLogger(__name__)
#
#
# class ProductProduct(models.Model):
#     _inherit = 'product.product'
#
#     # -------------------------------------------------------------------------
#     # Helper: reuse same logic as product.template
#     # -------------------------------------------------------------------------
#     def _generate_barcode(self):
#         """Delegate barcode generation to product.template helper."""
#         return self.env['product.template']._generate_barcode()
#
#     # -------------------------------------------------------------------------
#     # Override create: assign barcode to variants that don't have one
#     # (applies when variants are created independently, e.g. via attributes)
#     # -------------------------------------------------------------------------
#     @api.model_create_multi
#     def create(self, vals_list):
#         for vals in vals_list:
#             # Only auto-assign if barcode is absent AND the template barcode
#             # is not being set (multi-variant products need per-variant codes)
#             if not vals.get('barcode'):
#                 barcode = self._generate_barcode()
#                 if barcode:
#                     vals['barcode'] = barcode
#         return super().create(vals_list)
# -*- coding: utf-8 -*-
import logging
from odoo import api, models

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _generate_barcode(self):
        """Delegate barcode generation to product.template helper."""
        return self.env['product.template']._generate_barcode()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # 1) Variant already has a barcode — leave it alone
            if vals.get('barcode'):
                continue

            tmpl_id = vals.get('product_tmpl_id')

            if tmpl_id:
                tmpl = self.env['product.template'].sudo().browse(tmpl_id)

                # 2) Template already has a barcode (manually entered or auto-generated
                #    by the template's own create()) — do NOT overwrite with a new one
                if tmpl.exists() and tmpl.barcode:
                    continue

                # 3) Template has more than zero existing variants already —
                #    this is a new attribute variant; give it its own barcode
                existing_variants = self.env['product.product'].sudo().search_count(
                    [('product_tmpl_id', '=', tmpl_id)]
                )
                if existing_variants > 0:
                    barcode = self._generate_barcode()
                    if barcode:
                        vals['barcode'] = barcode
                # else: first variant — template create() already set the barcode,
                # we just skip and let the sync happen naturally

            # No template id at all — standalone variant, auto-generate
            elif not tmpl_id:
                barcode = self._generate_barcode()
                if barcode:
                    vals['barcode'] = barcode

        return super().create(vals_list)