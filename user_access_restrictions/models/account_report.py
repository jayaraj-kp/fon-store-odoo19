# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import AccessError


# Map: report action xml_id keyword  →  user restriction field
REPORT_RESTRICTION_MAP = {
    'balance_sheet': 'restrict_balance_sheet',
    'profit_loss': 'restrict_profit_loss',
    'partner_ledger': 'restrict_partner_ledger',
    'general_ledger': 'restrict_general_ledger',
    'trial_balance': 'restrict_trial_balance',
    'cash_flow': 'restrict_cash_flow',
    'aged_receivable': 'restrict_aged_receivable',
    'aged_payable': 'restrict_aged_payable',
    'tax_report': 'restrict_tax_report',
    'executive_summary': 'restrict_executive_summary',
}


class AccountReport(models.AbstractModel):
    """
    Hook into Odoo 17/18/19's account.report to block restricted users.
    Works together with menu-level hiding defined in report_menu_views.xml.
    """
    _inherit = 'account.report'

    def _get_options(self, previous_options=None):
        """Block report generation for restricted users."""
        user = self.env.user
        report_name = self._name  # e.g. 'account.balance.sheet'

        check_map = {
            'balance_sheet': 'restrict_balance_sheet',
            'profit.loss': 'restrict_profit_loss',
            'partner.ledger': 'restrict_partner_ledger',
            'general.ledger': 'restrict_general_ledger',
            'trial.balance': 'restrict_trial_balance',
            'cash.flow': 'restrict_cash_flow',
            'aged.receivable': 'restrict_aged_receivable',
            'aged.payable': 'restrict_aged_payable',
        }

        for keyword, field in check_map.items():
            if keyword in report_name and getattr(user, field, False):
                raise AccessError(
                    "You do not have permission to view this report. "
                    "Please contact your administrator."
                )

        return super()._get_options(previous_options=previous_options)
