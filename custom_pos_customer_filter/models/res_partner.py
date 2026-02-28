from odoo import models
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _load_pos_data_domain(self, data, config):
        _logger.warning("====== _load_pos_data_domain CALLED ======")
        # Don't call super() — replace entirely
        return [('parent_id', '!=', False)]

    def get_new_partner(self, partner_id):
        _logger.warning("====== get_new_partner CALLED id=%s ======", partner_id)
        result = super().get_new_partner(partner_id)
        _logger.warning("====== get_new_partner RESULT keys=%s ======",
                        list(result.keys()) if isinstance(result, dict) else type(result))
        return result