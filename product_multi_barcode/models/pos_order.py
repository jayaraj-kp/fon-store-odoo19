# -*- coding: utf-8 -*-
from odoo import models, api


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _loader_params_product_product(self):
        """
        Ensure barcode_2, barcode_3 and their qty/label fields are sent
        to the POS front-end so the JS barcode handler can resolve them.
        """
        result = super()._loader_params_product_product()
        result['search_params']['fields'] += [
            'barcode_2', 'package_qty_2', 'package_name_2',
            'barcode_3', 'package_qty_3', 'package_name_3',
        ]
        return result

    @api.model
    def _loader_params_product_template(self):
        result = super()._loader_params_product_template()
        result['search_params']['fields'] += [
            'barcode_2', 'package_qty_2', 'package_name_2',
            'barcode_3', 'package_qty_3', 'package_name_3',
        ]
        return result
