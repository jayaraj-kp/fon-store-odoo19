# -*- coding: utf-8 -*-
from odoo import models, fields, api


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
            "Leave empty to allow access to all POS terminals (admin behaviour)."
        ),
    )

    def get_allowed_pos_ids(self):
        """Return list of allowed POS config IDs for the current user.
        Returns False if no restriction is set (all POS accessible)."""
        self.ensure_one()
        if self.allowed_pos_ids:
            return self.allowed_pos_ids.ids
        return False
