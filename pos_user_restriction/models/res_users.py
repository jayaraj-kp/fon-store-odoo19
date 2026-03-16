# -*- coding: utf-8 -*-
from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    allowed_pos_ids = fields.Many2many(
        comodel_name='pos.config',
        relation='pos_config_res_users_rel',
        column1='user_id',
        column2='pos_config_id',
        string='Allowed POS',
        help="If set, this user can only access the listed Point of Sale configurations. "
             "Leave empty to allow access to all POS (no restriction).",
    )
