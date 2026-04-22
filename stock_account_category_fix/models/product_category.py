from odoo import fields, models
import logging

_logger = logging.getLogger(__name__)


class ProductCategory(models.Model):
    _inherit = 'product.category'

    property_stock_valuation_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Stock Valuation Account',
        company_dependent=True,
    )
    property_stock_journal = fields.Many2one(
        comodel_name='account.journal',
        string='Stock Journal',
        company_dependent=True,
    )
    property_stock_account_input_categ_id = fields.Many2one(
        comodel_name='account.account',
        string='Stock Input Account',
        company_dependent=True,
        default=lambda self: self._default_stock_input_account(),
    )
    property_stock_account_output_categ_id = fields.Many2one(
        comodel_name='account.account',
        string='Stock Output Account',
        company_dependent=True,
        default=lambda self: self._default_stock_output_account(),
    )

    def _default_stock_input_account(self):
        """
        Returns 'Stock Interim (Received) A/C' as default Stock Input Account.
        Account ID 63 in DB — searched by exact name since no XML ID exists.
        """
        account = self.env['account.account'].search(
            [('name', '=', 'Stock Interim (Received) A/C')], limit=1
        )
        if not account:
            # Fallback: partial match
            account = self.env['account.account'].search(
                [('name', 'ilike', 'Interim (Received)')], limit=1
            )
        if not account:
            _logger.warning("Stock Interim (Received) A/C not found in account.account")
        return account or False

    def _default_stock_output_account(self):
        """
        Returns 'Stock Interim (Deliverd) A/C' as default Stock Output Account.
        Account ID 64 in DB — searched by exact name since no XML ID exists.
        Note: 'Deliverd' is intentionally misspelled to match the actual account name in DB.
        """
        account = self.env['account.account'].search(
            [('name', '=', 'Stock Interim (Deliverd) A/C')], limit=1
        )
        if not account:
            # Fallback: partial match
            account = self.env['account.account'].search(
                [('name', 'ilike', 'Interim (Deliver')], limit=1
            )
        if not account:
            _logger.warning("Stock Interim (Deliverd) A/C not found in account.account")
        return account or False