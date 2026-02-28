from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

_logger.info("=" * 60)
_logger.info("[pos_cash_customer_contacts] res_partner.py IS LOADED")
_logger.info("=" * 60)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_cash_customer_id(self):
        """
        Find the correct Cash Customer parent partner ID.
        If multiple exist, pick the one that has children.
        """
        cash_customers = self.env['res.partner'].search(
            [('name', '=', 'Cash Customer'), ('active', '=', True)]
        )

        _logger.info(
            "[pos_cash_customer_contacts] _get_cash_customer_id: Found %d 'Cash Customer' records: %s",
            len(cash_customers),
            [(p.id, p.name, p.parent_id.id if p.parent_id else None) for p in cash_customers]
        )

        if not cash_customers:
            cash_customers = self.env['res.partner'].with_context(active_test=False).search(
                [('name', '=', 'Cash Customer')]
            )
            _logger.warning(
                "[pos_cash_customer_contacts] Including archived: %s",
                [(p.id, p.active) for p in cash_customers]
            )

        # Prefer the one that has children
        for cc in cash_customers:
            children = self.env['res.partner'].search([
                ('parent_id', '=', cc.id),
                ('active', '=', True),
            ], limit=1)
            if children:
                _logger.info(
                    "[pos_cash_customer_contacts] Using Cash Customer ID=%d (has children)", cc.id
                )
                return cc.id

        # Fallback: return the one with no parent (top-level)
        for cc in cash_customers:
            if not cc.parent_id:
                _logger.info(
                    "[pos_cash_customer_contacts] Using Cash Customer ID=%d (no parent, fallback)", cc.id
                )
                return cc.id

        if cash_customers:
            _logger.info(
                "[pos_cash_customer_contacts] Using first Cash Customer ID=%d", cash_customers[0].id
            )
            return cash_customers[0].id

        return False

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
            "[pos_cash_customer_contacts] _get_cash_customer_child_ids: "
            "Found %d contacts under Cash Customer ID=%d: %s",
            len(child_ids), parent_id, child_ids
        )
        return child_ids

    @api.model
    def get_new_partner(self, config_id, domain, offset):
        """
        Odoo 19: Called by JS for both live search and infinite scroll.
        Restrict results to Cash Customer children only.
        """
        _logger.info(
            "[pos_cash_customer_contacts] get_new_partner CALLED - "
            "config_id=%s domain=%s offset=%s", config_id, domain, offset
        )

        child_ids = self._get_cash_customer_child_ids()
        _logger.info(
            "[pos_cash_customer_contacts] get_new_partner: child_ids=%s", child_ids
        )

        restrict_domain = [('id', 'in', child_ids)]
        combined_domain = restrict_domain + (domain or [])
        _logger.info(
            "[pos_cash_customer_contacts] get_new_partner: combined_domain=%s", combined_domain
        )

        config = self.env['pos.config'].browse(config_id)
        new_partners = self.search(combined_domain, offset=offset, limit=100)
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
        Odoo 19: Called on initial POS session load.
        Restrict to Cash Customer children + Cash Customer itself + current user.
        """
        _logger.info("[pos_cash_customer_contacts] _load_pos_data_domain CALLED")

        child_ids = self._get_cash_customer_child_ids()
        child_ids_set = set(child_ids)

        # Include Cash Customer itself so JS can find it as parent reference
        cash_customer_id = self._get_cash_customer_id()
        if cash_customer_id:
            child_ids_set.add(cash_customer_id)
            _logger.info(
                "[pos_cash_customer_contacts] _load_pos_data_domain: "
                "Added Cash Customer ID=%d to set", cash_customer_id
            )
        else:
            _logger.warning(
                "[pos_cash_customer_contacts] _load_pos_data_domain: "
                "Cash Customer NOT FOUND — JS will not be able to filter!"
            )

        # Include current user's partner
        user_partner_id = self.env.user.partner_id.id
        child_ids_set.add(user_partner_id)
        _logger.info(
            "[pos_cash_customer_contacts] _load_pos_data_domain: "
            "Added current user partner ID=%d", user_partner_id
        )

        result = [('id', 'in', list(child_ids_set))]
        _logger.info(
            "[pos_cash_customer_contacts] _load_pos_data_domain: "
            "Final id set (count=%d): %s", len(child_ids_set), sorted(child_ids_set)
        )
        _logger.info(
            "[pos_cash_customer_contacts] _load_pos_data_domain returning domain: %s", result
        )
        return result