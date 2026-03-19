# -*- coding: utf-8 -*-
from odoo import models, fields


class PosConfig(models.Model):
    _inherit = 'pos.config'

    charity_enabled = fields.Boolean(
        string='Enable Charity Donations',
        default=False,
        help='Show a Charity button on the POS payment screen to allow customers to donate change.',
    )
    charity_account_id = fields.Many2one(
        'pos.charity.account',
        string='Charity Account',
        help='Select the charity ledger/account where donations will be recorded.',
        domain=[('active', '=', True)],
    )
    charity_button_label = fields.Char(
        string='Charity Button Label',
        default='Donate to Charity',
        help='Label displayed on the charity button in POS payment screen.',
    )
