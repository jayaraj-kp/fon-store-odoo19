from odoo import models
import logging

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _get_partners_domain(self):
        """
        Odoo 19 CE: This is the REAL method that controls which partners
        are loaded into POS. Override it to return only contacts
        (child partners) of 'Cash Customer'.
        """
        # Get the base domain from Odoo (usually just active partners)
        base_domain = super()._get_partners_domain()

        cash_customer = self.env['res.partner'].search(
            [('name', '=', 'Cash Customer'), ('active', '=', True)],
            limit=1
        )

        if not cash_customer:
            _logger.warning(
                "[pos_cash_customer_contacts] 'Cash Customer' partner not found! "
                "Showing no partners."
            )
            return [('id', '=', False)]

        child_ids = self.env['res.partner'].search([
            ('parent_id', '=', cash_customer.id),
            ('active', '=', True),
        ]).ids

        if not child_ids:
            _logger.warning(
                "[pos_cash_customer_contacts] No contacts found under 'Cash Customer'."
            )
            return [('id', '=', False)]

        _logger.info(
            "[pos_cash_customer_contacts] _get_partners_domain: restricting to %d contacts: %s",
            len(child_ids), child_ids
        )

        # Return domain restricted to only Cash Customer's children
        return [('id', 'in', child_ids)]