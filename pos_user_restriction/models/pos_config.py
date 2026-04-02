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
    def _get_pos_restriction_domain(self):
        """
        Returns a domain to restrict POS terminals for the current user,
        or an empty list if no restriction applies.
        """
        user = self.env.user
        if self._should_restrict_user(user):
            allowed_ids = self._get_allowed_pos_ids_for_user(user.id) or []
            return [('id', 'in', allowed_ids)]
        return []

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        """
        Inject POS restriction LAST (innermost AND) so it cannot be
        overridden by other modules that prepend their own domains.
        """
        restriction = self._get_pos_restriction_domain()
        if restriction:
            # Append after super so our filter always wins as a final AND
            ids = super()._search(domain, offset=0, limit=None, order=order, **kwargs)
            # Filter the result set directly using raw SQL allowed list
            allowed_ids = self._get_allowed_pos_ids_for_user(self.env.user.id) or []
            # Intersect: only keep ids that are in allowed_ids
            filtered = [i for i in ids if i in set(allowed_ids)]
            # Apply offset/limit after filtering
            if offset:
                filtered = filtered[offset:]
            if limit:
                filtered = filtered[:limit]
            return filtered
        return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, **kwargs):
        """
        Also restrict search_read — used by the POS dashboard and frontend.
        This catches cases where the dashboard bypasses _search.
        """
        restriction = self._get_pos_restriction_domain()
        if restriction:
            domain = list(domain or []) + restriction
        return super().search_read(domain=domain, fields=fields, offset=offset,
                                   limit=limit, order=order, **kwargs)

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



# # -*- coding: utf-8 -*-
# from odoo import models, fields, api, exceptions, _
#
#
# class PosConfig(models.Model):
#     _inherit = 'pos.config'
#
#     allowed_user_ids = fields.Many2many(
#         comodel_name='res.users',
#         relation='pos_config_users_rel',
#         column1='pos_config_id',
#         column2='user_id',
#         string='Allowed Users',
#         help="Users allowed to access this POS terminal.",
#     )
#
#     @api.model
#     def _get_allowed_pos_ids_for_user(self, user_id):
#         """
#         Fetch allowed POS config IDs for a user DIRECTLY via SQL.
#         This avoids any ORM call that could re-trigger _search and cause recursion.
#         Returns a list of IDs, or None if no restriction is set.
#         """
#         self.env.cr.execute(
#             """
#             SELECT pos_config_id
#             FROM pos_config_users_rel
#             WHERE user_id = %s
#             """,
#             (user_id,)
#         )
#         rows = self.env.cr.fetchall()
#         if rows:
#             return [r[0] for r in rows]
#         return None  # None means no restriction
#
#     @api.model
#     def _should_restrict_user(self, user):
#         """Check if user should be filtered, without triggering ORM recursion."""
#         if user._is_superuser():
#             return False
#         if user.has_group('base.group_system'):
#             return False
#         if user.has_group('point_of_sale.group_pos_manager'):
#             return False
#         # Use raw SQL to avoid recursion
#         allowed = self._get_allowed_pos_ids_for_user(user.id)
#         return allowed is not None  # restrict only if entries exist
#
#     @api.model
#     def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
#         user = self.env.user
#         if self._should_restrict_user(user):
#             allowed_ids = self._get_allowed_pos_ids_for_user(user.id) or []
#             restriction = [('id', 'in', allowed_ids)]
#             domain = restriction + list(domain) if domain else restriction
#         return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)
#
#     def open_ui(self):
#         self._check_pos_access()
#         return super().open_ui()
#
#     def open_session_cb(self, check_coa=True):
#         self._check_pos_access()
#         return super().open_session_cb(check_coa=check_coa)
#
#     def _check_pos_access(self):
#         user = self.env.user
#         if self._should_restrict_user(user):
#             allowed_ids = self._get_allowed_pos_ids_for_user(user.id) or []
#             for pos in self:
#                 if pos.id not in allowed_ids:
#                     raise exceptions.UserError(
#                         _("You are not allowed to access '%s'.\n"
#                           "Please contact your administrator.") % pos.name
#                     )
