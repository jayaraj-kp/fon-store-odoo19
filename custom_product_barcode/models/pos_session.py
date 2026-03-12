# -*- coding: utf-8 -*-
import logging
from odoo import models

_logger = logging.getLogger(__name__)

# Include price fields so JS can read them from the product object directly
CUSTOM_FIELDS = ['barcode2', 'barcode3', 'custom_qty1', 'custom_qty2', 'custom_price1', 'custom_price2']


class PosSession(models.Model):
    _inherit = 'pos.session'

    # Odoo 16 / 17 / 18
    def _loader_params_product_product(self):
        result = super()._loader_params_product_product()
        try:
            existing = result['search_params']['fields']
            for f in CUSTOM_FIELDS:
                if f not in existing:
                    existing.append(f)
            _logger.info('[CustomBarcode] _loader_params_product_product patched: %s', CUSTOM_FIELDS)
        except Exception as e:
            _logger.warning('[CustomBarcode] _loader_params_product_product patch failed: %s', e)
        return result

    # Odoo 19
    def _get_pos_ui_product_product(self, params):
        try:
            if 'fields' in params.get('search_params', {}):
                for f in CUSTOM_FIELDS:
                    if f not in params['search_params']['fields']:
                        params['search_params']['fields'].append(f)
        except Exception as e:
            _logger.warning('[CustomBarcode] _get_pos_ui_product_product patch failed: %s', e)
        return super()._get_pos_ui_product_product(params)