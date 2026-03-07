# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class CustomBarcodeController(http.Controller):

    @http.route('/pos/custom_barcode_map', type='json', auth='user', methods=['POST'], csrf=False)
    def get_custom_barcode_map(self, **kwargs):
        """
        Returns all custom package barcodes with qty and price.

        price logic:
          - If custom_price > 0  → use that fixed package price
          - If custom_price == 0 → use unit price × qty  (auto-calculated)
        """
        templates = request.env['product.template'].sudo().search([
            '|', ('barcode2', '!=', False), ('barcode3', '!=', False),
        ])

        result = {}
        for tmpl in templates:
            variant = tmpl.product_variant_ids[:1]
            if not variant:
                continue

            product_id   = variant.id
            product_name = tmpl.display_name
            unit_price   = tmpl.list_price

            if tmpl.barcode2 and tmpl.custom_qty1:
                # Use custom price if set, else unit_price × qty
                price = tmpl.custom_price1 if tmpl.custom_price1 > 0 else unit_price * tmpl.custom_qty1
                result[tmpl.barcode2] = {
                    'product_id':   product_id,
                    'product_name': product_name,
                    'qty':          tmpl.custom_qty1,
                    'price':        price,
                    'unit_price':   unit_price,
                }

            if tmpl.barcode3 and tmpl.custom_qty2:
                price = tmpl.custom_price2 if tmpl.custom_price2 > 0 else unit_price * tmpl.custom_qty2
                result[tmpl.barcode3] = {
                    'product_id':   product_id,
                    'product_name': product_name,
                    'qty':          tmpl.custom_qty2,
                    'price':        price,
                    'unit_price':   unit_price,
                }

        return {'barcodes': result}
