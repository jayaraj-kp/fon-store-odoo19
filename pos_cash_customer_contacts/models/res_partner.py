from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

_logger.info("=" * 60)
_logger.info("[pos_cash_customer_contacts] res_partner.py IS LOADED")
_logger.info("=" * 60)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_cash_customer_id(self):
        """Find the Cash Customer parent partner ID."""
        cash_customer = self.env['res.partner'].search(
            [('name', '=', 'Cash Customer'), ('active', '=', True)],
            limit=1
        )
        return cash_customer.id if cash_customer else False

    def _get_cash_customer_child_ids(self):
        """Return IDs of all contacts under Cash Customer."""
        parent_id = self._get_cash_customer_id()
        if not parent_id:
            _logger.warning("[pos_cash_customer_contacts] 'Cash Customer' not found!")
            return []
        child_ids = self.env['res.partner'].search([
            ('parent_id', '=', parent_id),
            ('active', '=', True),
        ]).ids
        _logger.info(
            "[pos_cash_customer_contacts] Found %d contacts under Cash Customer: %s",
            len(child_ids), child_ids
        )
        return child_ids

    @api.model
    def get_new_partner(self, config_id, domain, offset):
        """
        Odoo 19: Called by JS for both live search and infinite scroll.
        Restrict results to Cash Customer children only.
        """
        _logger.info("[pos_cash_customer_contacts] get_new_partner CALLED - config_id=%s domain=%s offset=%s", config_id, domain, offset)
        child_ids = self._get_cash_customer_child_ids()
        restrict_domain = [('id', 'in', child_ids)]
        combined_domain = restrict_domain + domain
        config = self.env['pos.config'].browse(config_id)
        new_partners = self.search(combined_domain, offset=offset, limit=100)
        fiscal_positions = new_partners.fiscal_position_id
        return {
            'res.partner': self._load_pos_data_read(new_partners, config),
            'account.fiscal.position': self.env['account.fiscal.position']._load_pos_data_read(
                fiscal_positions, config
            ),
        }

    @api.model
    def _load_pos_data_domain(self, data, config):
        """
        Odoo 19: Called on initial POS session load to determine
        which partners to preload. Restrict to Cash Customer children.
        Also include Cash Customer itself so JS can find it as parent reference.
        """
        _logger.info("[pos_cash_customer_contacts] _load_pos_data_domain CALLED")
        child_ids = self._get_cash_customer_child_ids()
        child_ids_set = set(child_ids)

        # Include Cash Customer itself so JS model can reference it
        cash_customer_id = self._get_cash_customer_id()
        if cash_customer_id:
            child_ids_set.add(cash_customer_id)

        # Include current user's partner
        child_ids_set.add(self.env.user.partner_id.id)

        result = [('id', 'in', list(child_ids_set))]
        _logger.info("[pos_cash_customer_contacts] _load_pos_data_domain returning: %s", result)
        return result



