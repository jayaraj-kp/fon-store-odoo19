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
        help="Users who are allowed to access this POS terminal. "
             "This is the reverse of 'Allowed POS' on the user form.",
    )

    def open_ui(self):
        """Block restricted users from opening an unauthorized POS."""
        self._check_pos_access()
        return super().open_ui()

    def open_session_cb(self, check_coa=True):
        """Block restricted users from opening a session on an unauthorized POS."""
        self._check_pos_access()
        return super().open_session_cb(check_coa=check_coa)

    def _check_pos_access(self):
        """Raise an error if the current user is not allowed to access this POS."""
        user = self.env.user
        if user._is_pos_restricted():
            for pos in self:
                if pos not in user.allowed_pos_ids:
                    raise exceptions.UserError(
                        _("You are not allowed to access the Point of Sale '%s'.\n"
                          "Please contact your administrator to grant you access.")
                        % pos.name
                    )


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _is_pos_restricted(self):
        """Return True if this user has POS restrictions configured."""
        self.ensure_one()
        if self._is_superuser():
            return False
        pos_manager_group = self.env.ref(
            'point_of_sale.group_pos_manager', raise_if_not_found=False
        )
        if pos_manager_group and pos_manager_group in self.groups_id:
            return False
        return bool(self.allowed_pos_ids)
