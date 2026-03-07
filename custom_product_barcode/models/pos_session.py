# -*- coding: utf-8 -*-
from odoo import models


class PosSession(models.Model):
    """
    Inject the custom barcode / qty fields into the POS data payload so the
    JavaScript layer can read them from product objects.

    Odoo 17-19 loads POS product data via pos.session._loader_params_product_product().
    We simply extend the fields list here.
    """

    _inherit = 'pos.session'

    def _loader_params_product_product(self):
        result = super()._loader_params_product_product()
        # Append the four new fields to whatever the base already loads
        result['search_params']['fields'].extend([
            'barcode2',
            'barcode3',
            'custom_qty1',
            'custom_qty2',
        ])
        return result
