# -*- coding: utf-8 -*-
from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    allowed_pos_ids = fields.Many2many(
        comodel_name='pos.config',
        relation='pos_config_users_rel',
        column1='user_id',
        column2='pos_config_id',
        string='Allowed POS',
        help=(
            "Assign specific Point of Sale terminals to this user. "
            "If set, the user will ONLY see and access the listed POS terminals. "
            "Leave empty to allow access to all POS terminals. "
            "Note: POS Managers always see all terminals regardless of this setting."
        ),
    )

    def _is_pos_restricted(self):
        """Return True only if this user is a plain POS User (not Manager/Admin)
        AND has specific allowed_pos_ids configured."""
        self.ensure_one()
        # Superuser → never restricted
        if self._is_superuser():
            return False
        # POS Manager group → never restricted
        pos_manager_group = self.env.ref(
            'point_of_sale.group_pos_manager', raise_if_not_found=False
        )
        if pos_manager_group and pos_manager_group in self.groups_id:
            return False
        # base.group_system (Administrator) → never restricted
        admin_group = self.env.ref('base.group_system', raise_if_not_found=False)
        if admin_group and admin_group in self.groups_id:
            return False
        # Only restrict if allowed_pos_ids is explicitly set
        return bool(self.allowed_pos_ids)
