from odoo import models
import logging

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_res_partner(self):
        """
        Odoo 16/17/18/19 CE: called at POS session load time.
        Restricts the domain to only child contacts of 'Cash Customer'.
        """
        result = super()._loader_params_res_partner()

        domain = self.env['res.partner']._get_cash_customer_child_domain()
        if domain is not None:
            result['search_params']['domain'] = domain
            _logger.info(
                "[pos_cash_customer_contacts] _loader_params_res_partner: domain=%s", domain
            )

        return result

    def get_pos_ui_res_partner_by_params(self, search_params):
        """
        Odoo 17/18/19: called for LIVE search when user types in POS customer search box.
        Overrides domain to only return Cash Customer children.
        """
        domain = self.env['res.partner']._get_cash_customer_child_domain()
        if domain is not None:
            # Combine: our filter AND whatever the user typed
            existing_domain = search_params.get('domain', [])
            search_params = dict(search_params)
            search_params['domain'] = domain + existing_domain

        return super().get_pos_ui_res_partner_by_params(search_params)