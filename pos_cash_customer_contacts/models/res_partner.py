from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

_logger.info("=" * 60)
_logger.info("[pos_cash_customer_contacts] res_partner.py IS LOADED")
_logger.info("=" * 60)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_cash_customer_id(self):
        cash_customers = self.env['res.partner'].search(
            [('name', '=', 'Cash Customer'), ('active', '=', True)]
        )
        _logger.info(
            "[pos_cash_customer_contacts] _get_cash_customer_id: Found %d records: %s",
            len(cash_customers),
            [(p.id, p.name, p.parent_id.id if p.parent_id else None) for p in cash_customers]
        )
        if not cash_customers:
            cash_customers = self.env['res.partner'].with_context(active_test=False).search(
                [('name', '=', 'Cash Customer')]
            )
        for cc in cash_customers:
            children = self.env['res.partner'].search(
                [('parent_id', '=', cc.id), ('active', '=', True)], limit=1
            )
            if children:
                _logger.info("[pos_cash_customer_contacts] Using Cash Customer ID=%d (has children)", cc.id)
                return cc.id
        for cc in cash_customers:
            if not cc.parent_id:
                _logger.info("[pos_cash_customer_contacts] Using Cash Customer ID=%d (no parent fallback)", cc.id)
                return cc.id
        if cash_customers:
            return cash_customers[0].id
        return False

    def _get_cash_customer_child_ids(self):
        parent_id = self._get_cash_customer_id()
        if not parent_id:
            _logger.warning("[pos_cash_customer_contacts] 'Cash Customer' not found!")
            return []
        child_ids = self.env['res.partner'].search([
            ('parent_id', '=', parent_id),
            ('active', '=', True),
        ]).ids
        _logger.info(
            "[pos_cash_customer_contacts] child_ids under Cash Customer ID=%d: %s",
            parent_id, child_ids
        )
        return child_ids

    def _load_pos_data_fields(self, config_id):
        """
        Odoo 19: Override to ensure parent_id is included in the fields
        loaded into the POS frontend model. Without this, parent_id is
        undefined in JS and filtering is impossible.
        """
        fields = super()._load_pos_data_fields(config_id)
        _logger.info(
            "[pos_cash_customer_contacts] _load_pos_data_fields CALLED - original fields: %s", fields
        )
        if 'parent_id' not in fields:
            fields.append('parent_id')
            _logger.info("[pos_cash_customer_contacts] Added 'parent_id' to POS partner fields")
        else:
            _logger.info("[pos_cash_customer_contacts] 'parent_id' already in fields")
        _logger.info(
            "[pos_cash_customer_contacts] _load_pos_data_fields FINAL fields: %s", fields
        )
        return fields

    @api.model
    def get_new_partner(self, config_id, domain, offset):
        """
        Odoo 19: Called by JS for live search and infinite scroll.
        Ignore incoming search domain — just return Cash Customer children.
        """
        _logger.info(
            "[pos_cash_customer_contacts] get_new_partner CALLED - config_id=%s offset=%s",
            config_id, offset
        )
        _logger.info(
            "[pos_cash_customer_contacts] get_new_partner: ignoring search domain=%s", domain
        )

        child_ids = self._get_cash_customer_child_ids()
        if not child_ids:
            _logger.warning("[pos_cash_customer_contacts] get_new_partner: no children, returning empty")
            return {'res.partner': [], 'account.fiscal.position': []}

        restrict_domain = [('id', 'in', child_ids)]
        _logger.info(
            "[pos_cash_customer_contacts] get_new_partner: domain=%s offset=%s",
            restrict_domain, offset
        )

        config = self.env['pos.config'].browse(config_id)
        new_partners = self.search(restrict_domain, offset=offset, limit=100)
        _logger.info(
            "[pos_cash_customer_contacts] get_new_partner: returning %d partners: %s",
            len(new_partners),
            [(p.id, p.name, p.parent_id.id if p.parent_id else None) for p in new_partners]
        )

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
        Called on initial POS session load.
        Load: children + Cash Customer itself (needed as parent ref in JS) + user partner.
        """
        _logger.info("[pos_cash_customer_contacts] _load_pos_data_domain CALLED")

        child_ids = self._get_cash_customer_child_ids()
        child_ids_set = set(child_ids)

        cash_customer_id = self._get_cash_customer_id()
        if cash_customer_id:
            child_ids_set.add(cash_customer_id)
            _logger.info("[pos_cash_customer_contacts] Added Cash Customer ID=%d", cash_customer_id)
        else:
            _logger.warning("[pos_cash_customer_contacts] Cash Customer NOT FOUND!")

        user_partner_id = self.env.user.partner_id.id
        child_ids_set.add(user_partner_id)

        result = [('id', 'in', list(child_ids_set))]
        _logger.info(
            "[pos_cash_customer_contacts] _load_pos_data_domain: set=%s domain=%s",
            sorted(child_ids_set), result
        )
        return result