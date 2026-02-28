from odoo import models
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _load_pos_data_domain(self, data, config):
        _logger.warning("====== CUSTOM: _load_pos_data_domain CALLED ======")
        domain = [('parent_id', '!=', False)]
        _logger.warning("====== domain: %s ======", domain)
        return domain

    def _load_pos_data_params(self, config):
        _logger.warning("====== CUSTOM: _load_pos_data_params CALLED ======")
        params = super()._load_pos_data_params(config)
        _logger.warning("====== ORIGINAL params: %s ======", params)

        # Override the domain inside params too
        params['domain'] = [('parent_id', '!=', False)]

        _logger.warning("====== FINAL params: %s ======", params)
        return params