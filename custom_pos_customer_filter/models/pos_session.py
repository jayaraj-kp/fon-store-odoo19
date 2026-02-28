from odoo import models
import logging

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = 'pos.session'

    def load_data(self, models_to_load):
        _logger.warning("====== CUSTOM: load_data CALLED ======")
        result = super().load_data(models_to_load)

        # Filter res.partner data after loading
        if 'res.partner' in result:
            before = len(result['res.partner'])

            result['res.partner'] = [
                p for p in result['res.partner']
                if p.get('parent_id') or p.get('customer_rank', 0) > 0
            ]

            after = len(result['res.partner'])
            _logger.warning("====== PARTNERS filtered: %s → %s ======", before, after)
        else:
            _logger.warning("====== res.partner NOT in result keys: %s ======", list(result.keys()))

        return result