# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _


class PosConfig(models.Model):
    _inherit = 'pos.config'

    allowed_user_ids = fields.Many2many(
        comodel_name='res.users',
        relation='pos_config_users_rel',
        column1='pos_config_id',
        column2='user_id',
        string='Allowed Users',
        help="Users allowed to access this POS terminal.",
    )

    @api.model
    def _get_allowed_pos_ids_for_user(self, user_id):
        """
        Fetch allowed POS config IDs for a user DIRECTLY via SQL.
        This avoids any ORM call that could re-trigger _search and cause recursion.
        Returns a list of IDs, or None if no restriction is set.
        """
        self.env.cr.execute(
            """
            SELECT pos_config_id
            FROM pos_config_users_rel
            WHERE user_id = %s
            """,
            (user_id,)
        )
        rows = self.env.cr.fetchall()
        if rows:
            return [r[0] for r in rows]
        return None  # None means no restriction

    @api.model
    def _should_restrict_user(self, user):
        """Check if user should be filtered, without triggering ORM recursion."""
        if user._is_superuser():
            return False
        if user.has_group('base.group_system'):
            return False
        if user.has_group('point_of_sale.group_pos_manager'):
            return False
        # Use raw SQL to avoid recursion
        allowed = self._get_allowed_pos_ids_for_user(user.id)
        return allowed is not None  # restrict only if entries exist

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        user = self.env.user
        if self._should_restrict_user(user):
            allowed_ids = self._get_allowed_pos_ids_for_user(user.id) or []
            restriction = [('id', 'in', allowed_ids)]
            domain = restriction + list(domain) if domain else restriction
        return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)

    def open_ui(self):
        self._check_pos_access()
        return super().open_ui()

    def open_session_cb(self, check_coa=True):
        self._check_pos_access()
        return super().open_session_cb(check_coa=check_coa)

    def _check_pos_access(self):
        user = self.env.user
        if self._should_restrict_user(user):
            allowed_ids = self._get_allowed_pos_ids_for_user(user.id) or []
            for pos in self:
                if pos.id not in allowed_ids:
                    raise exceptions.UserError(
                        _("You are not allowed to access '%s'.\n"
                          "Please contact your administrator.") % pos.name
                    )
