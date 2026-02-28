from odoo import models
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _load_pos_data_domain(self, data, config):
        _logger.warning("====== CUSTOM: _load_pos_data_domain CALLED ======")

        # Show ONLY child contacts (those with a parent company/customer)
        domain = [
            ('parent_id', '!=', False),
        ]

        _logger.warning("====== REPLACED domain: %s ======", domain)
        return domain