from odoo import models
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _load_pos_data_domain(self, data, config):
        _logger.warning("====== CUSTOM: _load_pos_data_domain CALLED ======")

        # REPLACE entire domain — do NOT append to parent
        # The parent domain is pre-loaded IDs which bypasses our filter
        domain = [
            '|',
            ('parent_id', '!=', False),
            ('customer_rank', '>', 0),
        ]

        _logger.warning("====== REPLACED domain: %s ======", domain)
        return domain