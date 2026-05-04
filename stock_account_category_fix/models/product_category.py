from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)


class ProductCategory(models.Model):
    _inherit = 'product.category'

    # -------------------------------------------------------------------------
    # These fields exist in stock_account but are not exposed in CE views.
    # We re-declare them here with company_dependent=True so they appear
    # in the Product Category form and behave as ir.property values per company.
    # -------------------------------------------------------------------------

    property_stock_valuation_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Stock Valuation Account',
        company_dependent=True,
        domain="[('deprecated', '=', False)]",
        help="Account used to value the inventory. Typically an asset account (e.g. 110100 Stock Valuation).",
        check_company=True,
    )

    property_stock_journal = fields.Many2one(
        comodel_name='account.journal',
        string='Stock Journal',
        company_dependent=True,
        domain="[('type', '=', 'general')]",
        help="Journal used to post inventory valuation moves (e.g. Inventory Valuation journal).",
        check_company=True,
    )

    property_stock_account_input_categ_id = fields.Many2one(
        comodel_name='account.account',
        string='Stock Input Account',
        company_dependent=True,
        domain="[('deprecated', '=', False)]",
        default=lambda self: self._default_stock_input_account(),
        help="Interim account debited when goods are received. Cleared when vendor bill is validated.",
        check_company=True,
    )

    property_stock_account_output_categ_id = fields.Many2one(
        comodel_name='account.account',
        string='Stock Output Account',
        company_dependent=True,
        domain="[('deprecated', '=', False)]",
        default=lambda self: self._default_stock_output_account(),
        help="Interim account credited when goods are delivered. Cleared when customer invoice is validated.",
        check_company=True,
    )

    # -------------------------------------------------------------------------
    # Default helpers
    # -------------------------------------------------------------------------

    def _default_stock_input_account(self):
        """
        Returns Stock Interim (Received) A/C as default input account.
        Searches by exact name first, then falls back to partial match.
        """
        Account = self.env['account.account']
        account = (
            Account.search([('name', '=', 'Stock Interim (Received) A/C')], limit=1)
            or Account.search([('name', 'ilike', 'Interim (Received)')], limit=1)
        )
        if not account:
            _logger.warning(
                "stock_account_category_fix: Could not find Stock Interim (Received) A/C "
                "in account.account. Please set Stock Input Account manually."
            )
        return account or False

    def _default_stock_output_account(self):
        """
        Returns Stock Interim (Deliverd) A/C as default output account.
        Note: 'Deliverd' spelling matches the actual account name in the database.
        """
        Account = self.env['account.account']
        account = (
            Account.search([('name', '=', 'Stock Interim (Deliverd) A/C')], limit=1)
            or Account.search([('name', 'ilike', 'Interim (Deliver')], limit=1)
        )
        if not account:
            _logger.warning(
                "stock_account_category_fix: Could not find Stock Interim (Deliverd) A/C "
                "in account.account. Please set Stock Output Account manually."
            )
        return account or False

    # -------------------------------------------------------------------------
    # Validation: warn if Perpetual valuation is set without required accounts
    # -------------------------------------------------------------------------

    @api.constrains(
        'property_valuation',
        'property_stock_valuation_account_id',
        'property_stock_journal',
        'property_stock_account_input_categ_id',
        'property_stock_account_output_categ_id',
    )
    def _check_perpetual_accounts(self):
        for cat in self:
            if cat.property_valuation == 'real_time':
                missing = []
                if not cat.property_stock_valuation_account_id:
                    missing.append('Stock Valuation Account')
                if not cat.property_stock_journal:
                    missing.append('Stock Journal')
                if not cat.property_stock_account_input_categ_id:
                    missing.append('Stock Input Account')
                if not cat.property_stock_account_output_categ_id:
                    missing.append('Stock Output Account')
                if missing:
                    _logger.warning(
                        "Product Category '%s' uses Perpetual valuation but is missing: %s. "
                        "Inventory accounting entries may not post correctly.",
                        cat.name, ', '.join(missing)
                    )
