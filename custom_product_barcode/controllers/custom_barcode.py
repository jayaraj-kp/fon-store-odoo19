# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json


class CustomBarcodeController(http.Controller):
    """
    Dedicated endpoint that returns a complete barcode→product map.

    The JS layer calls this once when the POS session opens, completely
    bypassing the POS product-loader field list (which proved unreliable
    across Odoo versions).

    GET /pos/custom_barcode_map?session_id=<int>
    Returns JSON:
    {
        "barcodes": {
            "<barcode_string>": {
                "product_id":   <int>,
                "product_name": "<str>",
                "qty":          <float>,
                "price":        <float>
            },
            ...
        }
    }
    """

    @http.route(
        '/pos/custom_barcode_map',
        type='json',
        auth='user',
        methods=['POST'],
        csrf=False,
    )
    def get_custom_barcode_map(self, session_id=None, **kwargs):
        """
        Return all products that have barcode2 or barcode3 set,
        together with the associated package qty and unit sales price.

        We query product.template (where the fields live) and resolve
        the canonical product.product variant for each.
        """
        env = request.env

        # Get all templates with at least one custom barcode
        templates = env['product.template'].sudo().search([
            '|',
            ('barcode2', '!=', False),
            ('barcode3', '!=', False),
        ])

        result = {}

        for tmpl in templates:
            # Use the first active variant — for simple (non-variant) products
            # there is always exactly one variant.
            variant = tmpl.product_variant_ids[:1]
            if not variant:
                continue

            product_id   = variant.id
            product_name = tmpl.display_name
            unit_price   = tmpl.list_price  # sales price

            if tmpl.barcode2 and tmpl.custom_qty1:
                result[tmpl.barcode2] = {
                    'product_id':   product_id,
                    'product_name': product_name,
                    'qty':          tmpl.custom_qty1,
                    'price':        unit_price,
                }

            if tmpl.barcode3 and tmpl.custom_qty2:
                result[tmpl.barcode3] = {
                    'product_id':   product_id,
                    'product_name': product_name,
                    'qty':          tmpl.custom_qty2,
                    'price':        unit_price,
                }

        return {'barcodes': result}
