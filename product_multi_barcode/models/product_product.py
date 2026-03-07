# -*- coding: utf-8 -*-
from odoo import models, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _search_by_barcode_multi(self, barcode):
        """
        Extends the standard barcode search to also check barcode_2 / barcode_3
        on the product template.  Returns (product, qty, label) or (False, 1, '').
        """
        if not barcode:
            return False, 1.0, ''

        # standard slot
        product = self.search([('barcode', '=', barcode)], limit=1)
        if product:
            return product, 1.0, product.display_name

        # template slot 2
        tmpl = self.env['product.template'].search(
            [('barcode_2', '=', barcode)], limit=1
        )
        if tmpl:
            qty = tmpl.package_qty_2 or 1.0
            label = tmpl.package_name_2 or ('%s – Pack 2' % tmpl.name)
            return tmpl.product_variant_id, qty, label

        # template slot 3
        tmpl = self.env['product.template'].search(
            [('barcode_3', '=', barcode)], limit=1
        )
        if tmpl:
            qty = tmpl.package_qty_3 or 1.0
            label = tmpl.package_name_3 or ('%s – Pack 3' % tmpl.name)
            return tmpl.product_variant_id, qty, label

        return False, 1.0, ''
