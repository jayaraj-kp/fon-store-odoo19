# Copyright 2024 YourCompany
# License: LGPL-3.0 or later

"""
Regression tests for two production-hardening fixes:

  1. analytic_account_ids is now capped at
     FinancialStatementsEnterpriseController._MAX_ANALYTIC_ACCOUNTS,
     mirroring the existing comparison_periods cap — get_data() re-runs
     a full report computation per selected analytic account, so an
     unbounded list is a real performance/DoS risk.

  2. An account whose *current*-period balance is (near) zero but which
     had a real balance in a *comparison* period used to disappear from
     the report entirely instead of showing "0.00 / <comparison value>".
     financial.report.engine._add_missing_comparison_leaves() fixes
     this by inserting a zero-balance placeholder leaf so the row (and
     its comparison figure) stays visible.
"""

import json

from odoo.tests import HttpCase, TransactionCase, tagged

from .common import FSEnterpriseCommon


def _find_line_by_account_id(lines, account_id):
    """Depth-first search for a report line by its account_id — unlike
    FSEnterpriseCommon.find_line (which searches by the structural
    ``id`` key), we don't know the synthetic id ahead of time here."""
    for line in lines:
        if line.get("account_id") == account_id:
            return line
        found = _find_line_by_account_id(line.get("children") or [], account_id)
        if found:
            return found
    return None


# ----------------------------------------------------------------------
# 1. analytic_account_ids cap
# ----------------------------------------------------------------------

@tagged("post_install", "-at_install")
class TestAnalyticAccountsCapped(HttpCase):
    """HTTP-level test — exercises the real controller cap, the same
    way test_controller_security.py proves the comparison_periods cap."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({"name": "Analytic Cap Test Co"})
        cls.user = cls.env["res.users"].create({
            "name": "Analytic Cap Tester",
            "login": "fs_analytic_cap_tester",
            "password": "fs_analytic_cap_tester",
            "company_id": cls.company.id,
            "company_ids": [(6, 0, [cls.company.id])],
            "groups_id": [(6, 0, [cls.env.ref("account.group_account_user").id])],
        })
        # Create more analytic accounts than the cap allows.
        cls.analytics = cls.env["account.analytic.account"].create([
            {"name": f"Analytic {i}", "company_id": cls.company.id}
            for i in range(30)
        ])

    def _json_rpc(self, url, params):
        payload = {"jsonrpc": "2.0", "method": "call", "params": params, "id": 1}
        return self.url_open(
            url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )

    def test_analytic_account_ids_capped_at_max(self):
        """More than _MAX_ANALYTIC_ACCOUNTS ids must be silently
        truncated, not fan out into dozens of extra report computations
        per request."""
        self.authenticate("fs_analytic_cap_tester", "fs_analytic_cap_tester")
        response = self._json_rpc("/fs_enterprise/get_data", {
            "report_type": "bs",
            "date_to": "2024-12-31",
            "company_id": self.company.id,
            "analytic_account_ids": self.analytics.ids,  # 30 ids
        })
        body = response.json()
        self.assertNotIn("error", body, body.get("error"))
        analytic_columns = body["result"].get("analytic_columns", [])
        # +1 for the always-appended "Total" column.
        self.assertLessEqual(len(analytic_columns), 20 + 1)

    def test_analytic_account_ids_under_cap_all_kept(self):
        """A request within the cap must not lose any columns."""
        self.authenticate("fs_analytic_cap_tester", "fs_analytic_cap_tester")
        small_set = self.analytics.ids[:5]
        response = self._json_rpc("/fs_enterprise/get_data", {
            "report_type": "bs",
            "date_to": "2024-12-31",
            "company_id": self.company.id,
            "analytic_account_ids": small_set,
        })
        body = response.json()
        self.assertNotIn("error", body)
        analytic_columns = body["result"].get("analytic_columns", [])
        # 5 selected accounts + 1 "Total" column.
        self.assertEqual(len(analytic_columns), 6)


# ----------------------------------------------------------------------
# 2. Disappearing comparison-only accounts
# ----------------------------------------------------------------------

@tagged("post_install", "-at_install")
class TestAddMissingComparisonLeavesPureLogic(TransactionCase):
    """Pure data-transform tests for _add_missing_comparison_leaves(),
    with no DB accounting fixtures needed — mirrors the style of
    test_report_engine_pure.py."""

    def setUp(self):
        super().setUp()
        self.engine = self.env["financial.report.engine"]

    def test_comparison_only_account_gets_placeholder_leaf(self):
        """An account present only in the comparison period must appear
        as a 0.0-balance row under its parent section, not disappear."""
        current_lines = [
            {
                "id": "bank_cash", "name": "Bank and Cash", "balance": 0.0,
                "children": [],
            },
        ]
        comparison_lines = [
            {
                "id": "bank_cash", "name": "Bank and Cash", "balance": 500.0,
                "children": [
                    {
                        "id": "bank_cash_acc_99", "name": "101000 Old Bank Account",
                        "line_type": "account", "style": "account", "level": 3,
                        "balance": 500.0, "account_id": 99, "children": [],
                    },
                ],
            },
        ]
        merged = self.engine.merge_comparison_lines(current_lines, comparison_lines)
        parent = merged[0]
        self.assertEqual(len(parent["children"]), 1)
        leaf = parent["children"][0]
        self.assertEqual(leaf["id"], "bank_cash_acc_99")
        self.assertEqual(leaf["account_id"], 99)
        # Current-period balance must stay 0 — this must not affect the
        # current period's own totals.
        self.assertEqual(leaf["balance"], 0.0)
        # ... but the comparison figure must be visible.
        self.assertEqual(leaf["comparison_balance"], 500.0)

    def test_account_present_in_both_periods_not_duplicated(self):
        """An account that already has a current-period row must not
        get a second, duplicate placeholder row."""
        current_lines = [
            {
                "id": "bank_cash", "name": "Bank and Cash", "balance": 200.0,
                "children": [
                    {
                        "id": "bank_cash_acc_5", "name": "101000 Bank",
                        "line_type": "account", "balance": 200.0,
                        "account_id": 5, "children": [],
                    },
                ],
            },
        ]
        comparison_lines = [
            {
                "id": "bank_cash", "name": "Bank and Cash", "balance": 150.0,
                "children": [
                    {
                        "id": "bank_cash_acc_5", "name": "101000 Bank",
                        "line_type": "account", "balance": 150.0,
                        "account_id": 5, "children": [],
                    },
                ],
            },
        ]
        merged = self.engine.merge_comparison_lines(current_lines, comparison_lines)
        self.assertEqual(len(merged[0]["children"]), 1)
        self.assertEqual(merged[0]["children"][0]["balance"], 200.0)
        self.assertEqual(merged[0]["children"][0]["comparison_balance"], 150.0)

    def test_unknown_parent_section_skipped_gracefully(self):
        """If the comparison leaf's parent section doesn't exist in the
        current tree at all (e.g. different report shape), the helper
        must skip it rather than raise."""
        current_lines = [{"id": "assets", "balance": 0.0, "children": []}]
        comparison_lines = [
            {
                "id": "some_other_section", "balance": 10.0, "children": [
                    {
                        "id": "some_other_section_acc_7", "name": "Ghost account",
                        "balance": 10.0, "account_id": 7, "children": [],
                    },
                ],
            },
        ]
        # Must not raise.
        merged = self.engine.merge_comparison_lines(current_lines, comparison_lines)
        self.assertEqual(merged[0]["children"], [])

    def test_multi_period_union_of_comparison_only_accounts(self):
        """merge_multi_comparison_lines(): an account only present in
        the *second* comparison period (not the first, not current)
        must still get a placeholder leaf, with only that period's
        column populated."""
        current_lines = [
            {"id": "bank_cash", "name": "Bank and Cash", "balance": 0.0, "children": []},
        ]
        periods = [
            {
                "label": "Q1", "date_to": "2023-03-31", "date_from": "2023-01-01",
                "lines": [{"id": "bank_cash", "balance": 0.0, "children": []}],
            },
            {
                "label": "Q2", "date_to": "2023-06-30", "date_from": "2023-04-01",
                "lines": [
                    {
                        "id": "bank_cash", "balance": 300.0, "children": [
                            {
                                "id": "bank_cash_acc_42", "name": "Closed sub-account",
                                "balance": 300.0, "account_id": 42, "children": [],
                            },
                        ],
                    },
                ],
            },
        ]
        merged = self.engine.merge_multi_comparison_lines(current_lines, periods)
        leaf = _find_line_by_account_id(merged, 42)
        self.assertIsNotNone(leaf, "comparison-only account must still appear as a row")
        self.assertEqual(leaf["balance"], 0.0)
        balances = [cb["balance"] for cb in leaf["comparison_balances"]]
        self.assertEqual(balances, [0.0, 300.0])


@tagged("post_install", "-at_install")
class TestDisappearingAccountEndToEnd(FSEnterpriseCommon):
    """Integration test: a real posted-then-reversed journal entry,
    through the actual get_balance_sheet() + merge_comparison_lines()
    pipeline, proves the fix end-to-end (not just against hand-built
    line dicts)."""

    def test_zeroed_out_account_still_shows_prior_balance_in_comparison(self):
        # 500 into the asset account in June 2023...
        self._post_entry("2023-06-01", [
            (self.account_asset, 500.0, 0.0),
            (self.account_payable, 0.0, 500.0),
        ])
        # ...fully reversed by December 2023, so the *cumulative*
        # balance as of the current period (2024) is back to zero and
        # _account_lines() would normally drop the row.
        self._post_entry("2023-12-01", [
            (self.account_asset, 0.0, 500.0),
            (self.account_payable, 500.0, 0.0),
        ])

        current = self.engine.get_balance_sheet(
            date_to="2024-12-31", company_id=self.company_data["company"].id,
        )
        comparison = self.engine.get_balance_sheet(
            date_to="2023-06-30", company_id=self.company_data["company"].id,
        )

        # Sanity check the fixture: the account really is 0 now, and
        # really was 500 as of the comparison date.
        comp_leaf = _find_line_by_account_id(comparison["lines"], self.account_asset.id)
        self.assertIsNotNone(comp_leaf)
        self.assertAlmostEqual(comp_leaf["balance"], 500.0)
        self.assertIsNone(
            _find_line_by_account_id(current["lines"], self.account_asset.id),
            "fixture assumption broken: account should have no current-period row",
        )

        merged_lines = self.engine.merge_comparison_lines(
            current["lines"], comparison["lines"]
        )
        merged_leaf = _find_line_by_account_id(merged_lines, self.account_asset.id)
        self.assertIsNotNone(
            merged_leaf,
            "account with a real comparison-period balance must not "
            "disappear from the report just because its current "
            "balance is zero",
        )
        self.assertAlmostEqual(merged_leaf["balance"], 0.0)
        self.assertAlmostEqual(merged_leaf["comparison_balance"], 500.0)