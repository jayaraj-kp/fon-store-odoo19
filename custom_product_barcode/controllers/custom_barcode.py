# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class CustomBarcodeController(http.Controller):

    @http.route('/pos/custom_barcode_map', type='json', auth='user', methods=['POST'], csrf=False)
    def get_custom_barcode_map(self, **kwargs):
        """
        Returns all custom package barcodes with qty, price and max_combo limit.

        price logic:
          - If custom_price > 0  → use that fixed package price (per unit)
          - If custom_price == 0 → fall back to standard unit price

        max_combo logic:
          - max_combo > 0 → maximum number of times this barcode can be scanned per bill
          - max_combo = 0 → unlimited
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
                price = tmpl.custom_price1 if tmpl.custom_price1 > 0 else unit_price
                result[tmpl.barcode2] = {
                    'product_id':   product_id,
                    'product_name': product_name,
                    'qty':          tmpl.custom_qty1,
                    'price':        price,
                    'unit_price':   unit_price,
                    'custom_price': tmpl.custom_price1 > 0,
                    'max_combo':    tmpl.max_combo_qty1,   # 0 = unlimited
                }

            if tmpl.barcode3 and tmpl.custom_qty2:
                price = tmpl.custom_price2 if tmpl.custom_price2 > 0 else unit_price
                result[tmpl.barcode3] = {
                    'product_id':   product_id,
                    'product_name': product_name,
                    'qty':          tmpl.custom_qty2,
                    'price':        price,
                    'unit_price':   unit_price,
                    'custom_price': tmpl.custom_price2 > 0,
                    'max_combo':    tmpl.max_combo_qty2,
                }

        return {'barcodes': result}
