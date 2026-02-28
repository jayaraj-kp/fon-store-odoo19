from odoo import models
import logging

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = 'pos.session'

    def load_data(self, models_to_load):
        result = super().load_data(models_to_load)
        if 'res.partner' in result:
            count = len(result['res.partner'])
            names = [p.get('name') for p in result['res.partner']]
            _logger.warning("====== PARTNERS COUNT: %s ======", count)
            _logger.warning("====== PARTNER NAMES: %s ======", names)
        return result