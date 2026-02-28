from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_cash_customer_child_domain(self):
        """Returns domain restricted to Cash Customer children."""
        cash_customer = self.search(
            [('name', '=', 'Cash Customer'), ('active', '=', True)],
            limit=1
        )
        if not cash_customer:
            return [('id', '=', False)]

        child_ids = self.search([
            ('parent_id', '=', cash_customer.id),
            ('active', '=', True),
        ]).ids

        return [('id', 'in', child_ids)] if child_ids else [('id', '=', False)]

    @api.model
    def get_new_partner(self, config_id, domain, offset):
        """
        Odoo 19 CE: JS calls this method for live search AND infinite scroll
        in the POS customer list. We inject our Cash Customer filter here.
        """
        cash_domain = self._get_cash_customer_child_domain()

        # Combine: our restriction AND user's search domain
        combined_domain = cash_domain + domain

        _logger.info(
            "[pos_cash_customer_contacts] get_new_partner called. "
            "Combined domain: %s, offset: %s", combined_domain, offset
        )

        return super().get_new_partner(config_id, combined_domain, offset)