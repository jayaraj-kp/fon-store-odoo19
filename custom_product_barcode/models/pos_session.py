# -*- coding: utf-8 -*-
import logging
from odoo import models

_logger = logging.getLogger(__name__)

CUSTOM_FIELDS = [
    'barcode2', 'barcode3',
    'custom_qty1', 'custom_qty2',
    'max_combo_qty1', 'max_combo_qty2',
]


class PosSession(models.Model):
    """
    Inject custom barcode/qty/max_combo fields into the POS product payload.

    Odoo renamed the loader method across versions:
      • Odoo 16/17  →  _loader_params_product_product()
      • Odoo 18/19  →  _get_fields_for_model('product.product', ...)
                       OR still _loader_params_product_product()

    We override ALL known variants so at least one will be active
    regardless of which Odoo 19 build is installed.
    """

    _inherit = 'pos.session'

    # ── Odoo 16 / 17 / 18 method ──────────────────────────────────────────────
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

    # ── Odoo 19 alternative — used when the above method no longer exists ─────
    def _get_pos_ui_product_product(self, params):
        """
        Odoo 19 CE renames/replaces _loader_params_product_product with this.
        We extend the fields list before passing to super.
        """
        try:
            if 'fields' in params.get('search_params', {}):
                for f in CUSTOM_FIELDS:
                    if f not in params['search_params']['fields']:
                        params['search_params']['fields'].append(f)
        except Exception as e:
            _logger.warning('[CustomBarcode] _get_pos_ui_product_product patch failed: %s', e)
        return super()._get_pos_ui_product_product(params)
