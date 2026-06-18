# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # -----------------------------------------------------------------------
    # Fields stored on res.company via related
    # -----------------------------------------------------------------------
    internal_transfer_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Internal Transfer Journal',
        related='company_id.internal_transfer_journal_id',
        readonly=False,
        domain=[('type', 'in', ['general', 'miscellaneous'])],
        help='Journal used to post internal stock transfer journal entries.',
    )

    internal_transfer_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Stock Transfer Account',
        related='company_id.internal_transfer_account_id',
        readonly=False,
        help='Account used for BOTH the debit and credit lines of the '
             'internal stock transfer journal entry.',
    )

    # -----------------------------------------------------------------------
    # Class method: fetch config for a given company (used in stock_picking)
    # -----------------------------------------------------------------------
    @api.model
    def _get_internal_transfer_config(self, company=None):
        """
        Returns a dict with 'journal' and 'account' for the given company.
        Falls back to env.company if none supplied.
        """
        company = company or self.env.company
        return {
            'journal': company.internal_transfer_journal_id,
            'account': company.internal_transfer_account_id,
        }


class ResCompany(models.Model):
    _inherit = 'res.company'

    internal_transfer_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Internal Transfer Journal',
        domain=[('type', 'in', ['general', 'miscellaneous'])],
        help='Journal used for internal stock transfer journal entries.',
    )

    internal_transfer_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Stock Transfer Account',
        help='Account used for both DR and CR lines of stock transfer entries.',
    )
