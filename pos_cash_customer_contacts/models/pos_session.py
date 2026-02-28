from odoo import models
import logging

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _get_pos_ui_res_partner(self, params):
        """
        Override to return only contacts (child partners) of the
        partner named 'Cash Customer'.
        Works with Odoo 16/17/18/19 CE.
        """
        params = self._filter_cash_customer_contacts(params)
        return super()._get_pos_ui_res_partner(params)

    def _loader_params_res_partner(self):
        """
        Odoo 17+ uses this method instead. Override domain here too.
        """
        result = super()._loader_params_res_partner()
        result = self._filter_cash_customer_contacts(result)
        return result

    def _filter_cash_customer_contacts(self, params):
        """
        Shared helper: restricts partner domain to only children
        of the 'Cash Customer' partner.
        """
        cash_customer = self.env['res.partner'].search(
            [('name', '=', 'Cash Customer'), ('active', '=', True)],
            limit=1
        )

        if cash_customer:
            child_ids = self.env['res.partner'].search([
                ('parent_id', '=', cash_customer.id),
                ('active', '=', True),
            ]).ids

            if child_ids:
                params.setdefault('search_params', {})
                params['search_params']['domain'] = [('id', 'in', child_ids)]
                _logger.info(
                    "[pos_cash_customer_contacts] Filtering to %d contacts under 'Cash Customer'.",
                    len(child_ids)
                )
            else:
                _logger.warning(
                    "[pos_cash_customer_contacts] No contacts found under 'Cash Customer'."
                )
                params.setdefault('search_params', {})
                params['search_params']['domain'] = [('id', '=', False)]
        else:
            _logger.warning(
                "[pos_cash_customer_contacts] 'Cash Customer' partner not found. "
                "Falling back to default partner list."
            )

        return params