# -*- coding: utf-8 -*-
from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_product_product(self):
        result = super()._loader_params_product_product()
        result['search_params']['fields'] += [
            'barcode_2', 'package_qty_2', 'package_name_2',
            'barcode_3', 'package_qty_3', 'package_name_3',
        ]
        return result
