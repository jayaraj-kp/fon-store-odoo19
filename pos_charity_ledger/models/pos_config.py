# -*- coding: utf-8 -*-
from odoo import models, fields


class PosConfig(models.Model):
    _inherit = 'pos.config'

    charity_enabled = fields.Boolean(string='Enable Charity Donations', default=False)
    charity_account_id = fields.Many2one(
        'pos.charity.account', string='Charity Account',
        domain=[('active', '=', True)],
    )
    charity_button_label = fields.Char(string='Charity Button Label', default='Donate to Charity')
    charity_gl_account_id = fields.Many2one(
        'account.account',
        string='Charity GL Account',
        help='The accounting account where charity donations will be credited (e.g. 201002 Charity).',
    )
    charity_journal_id = fields.Many2one(
        'account.journal',
        string='Charity Journal',
        help='Journal for charity entries. Leave empty to use POS Sales Journal.',
    )
