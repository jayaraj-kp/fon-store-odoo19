from odoo import models
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def get_new_partner(self, partner_id):
        _logger.warning("====== CUSTOM: get_new_partner CALLED id=%s ======", partner_id)
        result = super().get_new_partner(partner_id)
        _logger.warning("====== get_new_partner RESULT: %s ======", result)
        return result

    def _get_pos_partner_domain(self):
        """Override to filter only contacts with parent or customers"""
        domain = super()._get_pos_partner_domain() if hasattr(super(), '_get_pos_partner_domain') else []
        _logger.warning("====== CUSTOM: _get_pos_partner_domain CALLED ======")
        domain += [
            '|',
            ('parent_id', '!=', False),
            ('customer_rank', '>', 0),
        ]
        return domain

    def _load_pos_data_domain(self, data):
        _logger.warning("====== CUSTOM: _load_pos_data_domain CALLED ======")
        domain = super()._load_pos_data_domain(data)
        _logger.warning("====== ORIGINAL domain: %s ======", domain)
        domain += [
            '|',
            ('parent_id', '!=', False),
            ('customer_rank', '>', 0),
        ]
        _logger.warning("====== FINAL domain: %s ======", domain)
        return domain