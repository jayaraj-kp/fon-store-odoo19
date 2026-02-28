from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _get_partners_domain(self):
        _logger.warning("====== CUSTOM: _get_partners_domain CALLED ======")
        domain = super()._get_partners_domain()
        _logger.warning("====== ORIGINAL DOMAIN: %s ======", domain)
        domain += [
            '|',
            ('parent_id', '!=', False),
            ('customer_rank', '>', 0),
        ]
        _logger.warning("====== FINAL DOMAIN: %s ======", domain)
        return domain

    def load_data(self, models_to_load, only_data=False):
        _logger.warning("====== CUSTOM: load_data CALLED ======")
        result = super().load_data(models_to_load, only_data)
        _logger.warning("====== LOAD DATA KEYS: %s ======", list(result.keys()) if result else 'None')
        return result