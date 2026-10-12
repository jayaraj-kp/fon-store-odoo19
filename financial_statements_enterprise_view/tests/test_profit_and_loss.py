# Copyright 2024 YourCompany
# License: LGPL-3.0 or later

from odoo.tests import tagged

from .common import FSEnterpriseCommon


@tagged("post_install", "-at_install")
class TestProfitAndLoss(FSEnterpriseCommon):

    def test_gross_profit_and_net_profit(self):
        """1000 of revenue, 400 of operating expense -> Gross Profit 1000,
        Net Profit 600. Also checks the income sign-flip: income's raw
        balance is a credit, so revenue must still display as +1000."""
        self._post_entry("2024-03-10", [
            (self.account_receivable, 1000.0, 0.0),
            (self.account_revenue, 0.0, 1000.0),
        ])
        self._post_entry("2024-03-12", [
            (self.account_expense, 400.0, 0.0),
            (self.account_receivable, 0.0, 400.0),
        ])

        result = self.engine.get_profit_and_loss(
            date_from="2024-01-01", date_to="2024-12-31",
            company_id=self.company_data["company"].id,
        )
        revenue_line = self.find_line(result["lines"], "revenue")
        gross_profit = self.find_line(result["lines"], "gross_profit")
        net_profit = self.find_line(result["lines"], "net_profit")

        self.assertAlmostEqual(revenue_line["balance"], 1000.0)
        self.assertAlmostEqual(gross_profit["balance"], 1000.0)
        self.assertAlmostEqual(net_profit["balance"], 600.0)

    def test_period_boundaries_are_respected(self):
        """A transaction dated before date_from must not leak into the
        P&L for the requested period."""
        self._post_entry("2023-12-31", [
            (self.account_receivable, 500.0, 0.0),
            (self.account_revenue, 0.0, 500.0),
        ])
        result = self.engine.get_profit_and_loss(
            date_from="2024-01-01", date_to="2024-12-31",
            company_id=self.company_data["company"].id,
        )
        revenue_line = self.find_line(result["lines"], "revenue")
        self.assertAlmostEqual((revenue_line or {}).get("balance", 0.0), 0.0)

    def test_net_profit_zero_when_no_transactions(self):
        result = self.engine.get_profit_and_loss(
            date_from="2024-01-01", date_to="2024-12-31",
            company_id=self.company_data["company"].id,
        )
        net_profit = self.find_line(result["lines"], "net_profit")
        self.assertAlmostEqual(net_profit["balance"], 0.0)


@tagged("post_install", "-at_install")
class TestHasUnpostedEntries(FSEnterpriseCommon):

    def test_true_when_draft_move_in_range(self):
        self.env["account.move"].create({
            "move_type": "entry",
            "date": "2024-05-01",
            "journal_id": self.journal_misc.id,
            "line_ids": [
                (0, 0, {"account_id": self.account_asset.id,
                        "debit": 10.0, "credit": 0.0, "name": "/"}),
                (0, 0, {"account_id": self.account_payable.id,
                        "debit": 0.0, "credit": 10.0, "name": "/"}),
            ],
        })  # left in draft
        has_unposted = self.engine.has_unposted_entries(
            date_from="2024-01-01", date_to="2024-12-31",
            company_id=self.company_data["company"].id,
        )
        self.assertTrue(has_unposted)

    def test_false_when_draft_move_outside_range(self):
        """FIX regression: has_unposted_entries must honor date_from too,
        not just date_to, otherwise a draft move from a different period
        would incorrectly flag the current period."""
        self.env["account.move"].create({
            "move_type": "entry",
            "date": "2022-01-01",
            "journal_id": self.journal_misc.id,
            "line_ids": [
                (0, 0, {"account_id": self.account_asset.id,
                        "debit": 10.0, "credit": 0.0, "name": "/"}),
                (0, 0, {"account_id": self.account_payable.id,
                        "debit": 0.0, "credit": 10.0, "name": "/"}),
            ],
        })
        has_unposted = self.engine.has_unposted_entries(
            date_from="2024-01-01", date_to="2024-12-31",
            company_id=self.company_data["company"].id,
        )
        self.assertFalse(has_unposted)

    def test_false_when_all_posted(self):
        self._post_entry("2024-05-01", [
            (self.account_asset, 10.0, 0.0),
            (self.account_payable, 0.0, 10.0),
        ])
        has_unposted = self.engine.has_unposted_entries(
            date_from="2024-01-01", date_to="2024-12-31",
            company_id=self.company_data["company"].id,
        )
        self.assertFalse(has_unposted)