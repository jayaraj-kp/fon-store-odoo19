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
#         Avoids ORM calls that could cause recursion.
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
#         allowed = self._get_allowed_pos_ids_for_user(user.id)
#         return allowed is not None
#
#     @api.model
#     def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
#         """
#         Inject restriction as a simple domain clause.
#         IMPORTANT: Always return super()._search() directly so Odoo 19
#         receives the expected Query object — never return a plain list.
#         """
#         user = self.env.user
#         if self._should_restrict_user(user):
#             allowed_ids = self._get_allowed_pos_ids_for_user(user.id) or []
#             # Prepend restriction so it ANDs with whatever domain follows
#             domain = [('id', 'in', allowed_ids)] + list(domain or [])
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
#         """
#         Hard block: even if _search is bypassed by another module,
#         the user cannot actually open a POS they are not assigned to.
#         """
#         user = self.env.user
#         if self._should_restrict_user(user):
#             allowed_ids = self._get_allowed_pos_ids_for_user(user.id) or []
#             for pos in self:
#                 if pos.id not in allowed_ids:
#                     raise exceptions.UserError(
#                         _("You are not allowed to access '%s'.\n"
#                           "Please contact your administrator.") % pos.name
#                     )
#
#
#after review check i change into below code date in 20/10/2026
# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _

try:
    from odoo.fields import Domain  # Odoo 19+
except ImportError:  # pragma: no cover
    Domain = None


class PosConfig(models.Model):
    _inherit = 'pos.config'

    # NOTE: relation / column names are unchanged on purpose,
    # so the existing live data and table are reused as-is.
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
        Allowed POS ids for a user via direct SQL (no ORM recursion).
        Returns a list of ids, or None when no restriction is set.
        """
        # Make sure pending ORM writes on the relation are in the DB first,
        # otherwise the SQL below could read stale data in the same transaction.
        self.env['pos.config'].flush_model(['allowed_user_ids'])
        self.env['res.users'].flush_model(['allowed_pos_ids'])
        self.env.cr.execute(
            "SELECT pos_config_id FROM pos_config_users_rel WHERE user_id = %s",
            (user_id,),
        )
        rows = self.env.cr.fetchall()
        if rows:
            return [r[0] for r in rows]
        return None  # None means no restriction

    @api.model
    def _should_restrict_user(self, user):
        """True only if this user must be filtered."""
        if self.env.su or user._is_superuser():
            # sudo() / OdooBot: internal code must see every terminal
            return False
        if user.has_group('base.group_system'):
            return False
        if user.has_group('point_of_sale.group_pos_manager'):
            return False
        return self._get_allowed_pos_ids_for_user(user.id) is not None

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        """Always returns super()._search() so Odoo receives a Query object."""
        user = self.env.user
        if self._should_restrict_user(user):
            allowed_ids = self._get_allowed_pos_ids_for_user(user.id) or []
            restriction = [('id', 'in', allowed_ids)]
            if Domain is not None:
                domain = Domain(restriction) & Domain(domain if domain is not None else [])
            else:
                domain = restriction + list(domain or [])
        return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)

    def open_ui(self):
        self._check_pos_access()
        return super().open_ui()

    def open_session_cb(self, check_coa=True):
        self._check_pos_access()
        return super().open_session_cb(check_coa=check_coa)

    def _check_pos_access(self):
        """Hard block even if _search is bypassed by another module."""
        user = self.env.user
        if self._should_restrict_user(user):
            allowed_ids = self._get_allowed_pos_ids_for_user(user.id) or []
            for pos in self:
                if pos.id not in allowed_ids:
                    raise exceptions.UserError(
                        _("You are not allowed to access '%s'.\n"
                          "Please contact your administrator.") % pos.name
                    )