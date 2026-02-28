from odoo import models
import logging

_logger = logging.getLogger(__name__)


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def get_limited_partners_loading(self, offset=0):
        """
        Odoo 19: This SQL query decides which partners are preloaded
        into POS on session start. Override to return only children
        of the 'Cash Customer' partner.
        """
        cash_customer = self.env['res.partner'].search(
            [('name', '=', 'Cash Customer'), ('active', '=', True)],
            limit=1
        )

        if not cash_customer:
            _logger.warning(
                "[pos_cash_customer_contacts] 'Cash Customer' not found in get_limited_partners_loading."
            )
            return []

        child_partners = self.env['res.partner'].search([
            ('parent_id', '=', cash_customer.id),
            ('active', '=', True),
        ])

        _logger.info(
            "[pos_cash_customer_contacts] get_limited_partners_loading: "
            "returning %d contacts", len(child_partners)
        )

        # Return as list of tuples (id,) to match original format
        return [(p.id,) for p in child_partners]