from odoo import models
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _load_pos_data_domain(self, data, config):
        _logger.warning("====== CUSTOM: _load_pos_data_domain CALLED ======")
        domain = super()._load_pos_data_domain(data, config)
        _logger.warning("====== ORIGINAL domain: %s ======", domain)

        domain += [
            '|',
            ('parent_id', '!=', False),
            ('customer_rank', '>', 0),
        ]

        _logger.warning("====== FINAL domain: %s ======", domain)
        return domain