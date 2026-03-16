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
        help="Users who are allowed to access this POS terminal.",
    )

    def open_ui(self):
        self._check_pos_access()
        return super().open_ui()

    def open_session_cb(self, check_coa=True):
        self._check_pos_access()
        return super().open_session_cb(check_coa=check_coa)

    def _check_pos_access(self):
        user = self.env.user
        if user._is_pos_restricted():
            for pos in self:
                if pos not in user.allowed_pos_ids:
                    raise exceptions.UserError(
                        _("You are not allowed to access '%s'.\n"
                          "Please contact your administrator.") % pos.name
                    )


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _is_pos_restricted(self):
        """Return True only if this is a plain POS cashier with restrictions set."""
        self.ensure_one()

        # Superuser → never restricted
        if self._is_superuser():
            return False

        # Check groups using has_group() — works in all Odoo versions
        # POS Manager → never restricted
        if self.has_group('point_of_sale.group_pos_manager'):
            return False

        # System Administrator → never restricted
        if self.has_group('base.group_system'):
            return False

        # Only restrict if allowed_pos_ids is explicitly configured
        return bool(self.sudo().allowed_pos_ids)
