# Copyright 2024 YourCompany
# License: LGPL-3.0 or later

from odoo.tests import tagged

from .common import FSEnterpriseCommon


@tagged("post_install", "-at_install")
class TestBalanceSheet(FSEnterpriseCommon):

    def test_assets_equal_liabilities_when_no_equity(self):
        """Debit an asset, credit a liability for the same amount: the
        balance sheet must show ASSETS == LIABILITIES with EQUITY at 0.
        This proves both the accounting equation AND the sign-flip in
        _display_liability are correct — a common source of Balance
        Sheet bugs is liabilities showing up negative."""
        self._post_entry("2024-06-15", [
            (self.account_asset, 1000.0, 0.0),
            (self.account_payable, 0.0, 1000.0),
        ])
        result = self.engine.get_balance_sheet(
            date_to="2024-12-31",
            company_id=self.company_data["company"].id,
        )
        assets = self.find_line(result["lines"], "assets")
        liabilities = self.find_line(result["lines"], "liabilities")
        equity = self.find_line(result["lines"], "equity")

        self.assertAlmostEqual(assets["balance"], 1000.0)
        self.assertAlmostEqual(liabilities["balance"], 1000.0)
        self.assertAlmostEqual(equity["balance"], 0.0)

    def test_draft_entries_excluded_by_default(self):
        """target_move='posted' (the default) must ignore draft moves."""
        self.env["account.move"].create({
            "move_type": "entry",
            "date": "2024-06-15",
            "journal_id": self.journal_misc.id,
            "line_ids": [
                (0, 0, {"account_id": self.account_asset.id,
                        "debit": 500.0, "credit": 0.0, "name": "/"}),
                (0, 0, {"account_id": self.account_payable.id,
                        "debit": 0.0, "credit": 500.0, "name": "/"}),
            ],
        })  # deliberately left in draft state, never posted

        result = self.engine.get_balance_sheet(
            date_to="2024-12-31",
            company_id=self.company_data["company"].id,
            target_move="posted",
        )
        assets = self.find_line(result["lines"], "assets")
        self.assertAlmostEqual((assets or {}).get("balance", 0.0), 0.0)

    def test_draft_entries_included_when_requested(self):
        """target_move='all' must include draft moves too."""
        self.env["account.move"].create({
            "move_type": "entry",
            "date": "2024-06-15",
            "journal_id": self.journal_misc.id,
            "line_ids": [
                (0, 0, {"account_id": self.account_asset.id,
                        "debit": 500.0, "credit": 0.0, "name": "/"}),
                (0, 0, {"account_id": self.account_payable.id,
                        "debit": 0.0, "credit": 500.0, "name": "/"}),
            ],
        })
        result = self.engine.get_balance_sheet(
            date_to="2024-12-31",
            company_id=self.company_data["company"].id,
            target_move="all",
        )
        assets = self.find_line(result["lines"], "assets")
        self.assertAlmostEqual(assets["balance"], 500.0)

    def test_analytic_account_filter(self):
        """Passing analytic_account_ids must restrict computed balances
        to lines carrying that analytic distribution, without affecting
        the unfiltered totals."""
        analytic = self.env["account.analytic.account"].create({
            "name": "Test Analytic",
            "company_id": self.company_data["company"].id,
        })
        self._post_entry("2024-06-15", [
            (self.account_asset, 200.0, 0.0),
            (self.account_payable, 0.0, 200.0),
        ])
        # a second, unrelated entry with no analytic distribution
        self._post_entry("2024-06-16", [
            (self.account_asset, 300.0, 0.0),
            (self.account_payable, 0.0, 300.0),
        ])
        # attach the analytic account to only the first entry's line
        first_asset_line = self.env["account.move.line"].search([
            ("account_id", "=", self.account_asset.id),
            ("debit", "=", 200.0),
        ], limit=1)
        first_asset_line.analytic_distribution = {str(analytic.id): 100.0}

        result_all = self.engine.get_balance_sheet(
            date_to="2024-12-31", company_id=self.company_data["company"].id,
        )
        result_filtered = self.engine.get_balance_sheet(
            date_to="2024-12-31", company_id=self.company_data["company"].id,
            analytic_account_ids=[analytic.id],
        )
        assets_all = self.find_line(result_all["lines"], "assets")
        assets_filtered = self.find_line(result_filtered["lines"], "assets")

        self.assertAlmostEqual(assets_all["balance"], 500.0)
        self.assertAlmostEqual(assets_filtered["balance"], 200.0)

    def test_with_debit_credit_totals_match(self):
        """When with_debit_credit=True, every leaf account line must
        expose debit/credit that nets to the same displayed balance."""
        self._post_entry("2024-06-15", [
            (self.account_asset, 750.0, 0.0),
            (self.account_payable, 0.0, 750.0),
        ])
        result = self.engine.get_balance_sheet(
            date_to="2024-12-31",
            company_id=self.company_data["company"].id,
            with_debit_credit=True,
        )
        assets = self.find_line(result["lines"], "assets")
        self.assertAlmostEqual(assets["debit"] - assets["credit"], 750.0)