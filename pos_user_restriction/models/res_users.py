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
            "Assign specific POS terminals to this user. "
            "If set, the user will ONLY see those terminals on the POS dashboard. "
            "Leave empty to allow access to all terminals. "
            "POS Managers and Administrators always see all terminals."
        ),
    )
