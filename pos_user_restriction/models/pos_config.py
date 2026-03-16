# -*- coding: utf-8 -*-
from odoo import models, api, fields


class PosConfig(models.Model):
    _inherit = 'pos.config'

    # ---------------------------------------------------------------
    # Computed helper: is the current user restricted to specific POS?
    # ---------------------------------------------------------------
    @api.model
    def _get_allowed_pos_ids_for_user(self):
        """
        Returns a list of pos.config IDs the current user is allowed to open.
        Returns None when there is no restriction (empty allowed_pos_ids).
        """
        user = self.env.user
        # Administrators (base.group_system) bypass all restrictions
        if self.env.user.has_group('base.group_system'):
            return None
        allowed = user.allowed_pos_ids
        if not allowed:
            # No restriction configured → user can access everything
            return None
        return allowed.ids

    # ---------------------------------------------------------------
    # Override name_search so the dropdown only shows allowed POS
    # ---------------------------------------------------------------
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        allowed_ids = self._get_allowed_pos_ids_for_user()
        if allowed_ids is not None:
            args = [('id', 'in', allowed_ids)] + args
        return super().name_search(name=name, args=args, operator=operator, limit=limit)

    # ---------------------------------------------------------------
    # Override search_read (used by POS dashboard list)
    # ---------------------------------------------------------------
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        allowed_ids = self._get_allowed_pos_ids_for_user()
        if allowed_ids is not None:
            domain = [('id', 'in', allowed_ids)] + domain
        return super().search_read(domain=domain, fields=fields, offset=offset,
                                   limit=limit, order=order)

    # ---------------------------------------------------------------
    # Override search (used internally by many Odoo calls)
    # ---------------------------------------------------------------
    @api.model
    def search(self, domain, offset=0, limit=None, order=None, count=False):
        allowed_ids = self._get_allowed_pos_ids_for_user()
        if allowed_ids is not None:
            domain = [('id', 'in', allowed_ids)] + list(domain)
        return super().search(domain, offset=offset, limit=limit,
                              order=order, count=count)

    # ---------------------------------------------------------------
    # Prevent opening a session for a non-allowed POS via direct URL
    # ---------------------------------------------------------------
    def open_ui(self):
        self._check_pos_access()
        return super().open_ui()

    def open_session_cb(self, check_coa=True):
        self._check_pos_access()
        return super().open_session_cb(check_coa=check_coa)

    def _check_pos_access(self):
        """Raise an error if the current user is not allowed to access this POS."""
        from odoo.exceptions import AccessError
        allowed_ids = self._get_allowed_pos_ids_for_user()
        if allowed_ids is not None:
            for rec in self:
                if rec.id not in allowed_ids:
                    raise AccessError(
                        f"You are not allowed to access the POS '{rec.name}'. "
                        "Please contact your administrator."
                    )
