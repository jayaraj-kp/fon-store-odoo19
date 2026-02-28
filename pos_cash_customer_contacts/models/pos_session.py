from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _get_pos_ui_res_partner(self, params):
        """
        Override to return only contacts (child partners) of the
        partner named 'Cash Customer'.
        """
        # Find the Cash Customer parent record
        cash_customer = self.env['res.partner'].search(
            [('name', '=', 'Cash Customer'), ('active', '=', True)],
            limit=1
        )

        if cash_customer:
            # Override the domain to only fetch children of Cash Customer
            # Get child contact IDs
            child_ids = self.env['res.partner'].search([
                ('parent_id', '=', cash_customer.id),
                ('active', '=', True),
            ]).ids

            if child_ids:
                # Temporarily patch the search domain in params
                params['search_params']['domain'] = [('id', 'in', child_ids)]
            else:
                _logger.warning(
                    "No contacts found under 'Cash Customer'. "
                    "Returning empty partner list."
                )
                params['search_params']['domain'] = [('id', '=', False)]
        else:
            _logger.warning(
                "'Cash Customer' partner not found. "
                "Falling back to default POS partner list."
            )

        return super()._get_pos_ui_res_partner(params)