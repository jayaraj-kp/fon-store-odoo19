from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_cash_customer_child_domain(self):
        """Returns domain restricted to Cash Customer children, or None if not found."""
        cash_customer = self.search(
            [('name', '=', 'Cash Customer'), ('active', '=', True)],
            limit=1
        )
        if not cash_customer:
            _logger.warning("[pos_cash_customer_contacts] 'Cash Customer' partner not found.")
            return None

        child_ids = self.search([
            ('parent_id', '=', cash_customer.id),
            ('active', '=', True),
        ]).ids

        if child_ids:
            return [('id', 'in', child_ids)]
        return [('id', '=', False)]