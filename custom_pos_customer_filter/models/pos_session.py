from odoo import models
import logging

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _get_partners_domain(self):
        _logger.warning("=== CUSTOM POS FILTER: _get_partners_domain CALLED ===")
        domain = super()._get_partners_domain()
        _logger.warning("=== ORIGINAL DOMAIN: %s ===", domain)

        # Filter: show only child contacts + main customers
        extra_domain = [
            '|',
            ('parent_id', '!=', False),
            ('customer_rank', '>', 0),
        ]

        final_domain = domain + extra_domain
        _logger.warning("=== FINAL DOMAIN: %s ===", final_domain)
        return final_domain