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
    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        """
        Inject POS restriction into every search for non-admin users.
        **kwargs absorbs Odoo 19's extra args like bypass_access without breaking.
        """
        user = self.env.user

        if self._should_restrict(user):
            allowed_ids = user.sudo().allowed_pos_ids.ids
            restriction = [('id', 'in', allowed_ids)]
            domain = restriction + list(domain) if domain else restriction

        return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)

    @api.model
    def _should_restrict(self, user):
        """Return True if POS filtering should apply to this user."""
        if user._is_superuser():
            return False
        if user.has_group('base.group_system'):
            return False
        if user.has_group('point_of_sale.group_pos_manager'):
            return False
        # Only restrict if the user actually has allowed_pos_ids configured
        return bool(user.sudo().allowed_pos_ids)

    def open_ui(self):
        self._check_pos_access()
        return super().open_ui()

    def open_session_cb(self, check_coa=True):
        self._check_pos_access()
        return super().open_session_cb(check_coa=check_coa)

    def _check_pos_access(self):
        user = self.env.user
        if self._should_restrict(user):
            allowed_ids = user.sudo().allowed_pos_ids.ids
            for pos in self:
                if pos.id not in allowed_ids:
                    raise exceptions.UserError(
                        _("You are not allowed to access '%s'.\n"
                          "Please contact your administrator.") % pos.name
                    )
