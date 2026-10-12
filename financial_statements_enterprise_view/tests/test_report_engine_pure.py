# Copyright 2024 YourCompany
# License: LGPL-3.0 or later

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestReportEnginePureLogic(TransactionCase):
    """Tests for the report-tree helpers that are pure data transforms
    (no DB queries), so they run fast and don't need any accounting
    fixtures. These cover the two documented FIX comments in
    financial_report_engine.py around comparison merging.
    """

    def setUp(self):
        super().setUp()
        self.engine = self.env["financial.report.engine"]

    # ------------------------------------------------------------------
    # merge_comparison_lines
    # ------------------------------------------------------------------

    def test_merge_comparison_lines_single_period(self):
        current = [
            {"id": "assets", "balance": 1000.0, "children": [
                {"id": "cash", "balance": 400.0, "children": []},
            ]},
        ]
        comparison = [
            {"id": "assets", "balance": 800.0, "children": [
                {"id": "cash", "balance": 300.0, "children": []},
            ]},
        ]
        merged = self.engine.merge_comparison_lines(current, comparison)
        self.assertEqual(merged[0]["comparison_balance"], 800.0)
        self.assertEqual(merged[0]["children"][0]["comparison_balance"], 300.0)
        # FIX (#comparison_balances): must also populate the uniform
        # single-item list used by the PDF/screen templates.
        self.assertEqual(merged[0]["comparison_balances"], [{"balance": 800.0}])

    def test_merge_comparison_lines_missing_id_defaults_to_zero(self):
        """A line id that didn't exist in the comparison period (e.g. a
        newly created account) must default to 0, not KeyError."""
        current = [{"id": "new_line", "balance": 50.0, "children": []}]
        comparison = [{"id": "other_line", "balance": 999.0, "children": []}]
        merged = self.engine.merge_comparison_lines(current, comparison)
        self.assertEqual(merged[0]["comparison_balance"], 0.0)

    # ------------------------------------------------------------------
    # merge_multi_comparison_lines
    # ------------------------------------------------------------------

    def test_merge_multi_comparison_lines_no_late_binding_bug(self):
        """Regression test for the documented closure fix: each period's
        comparison map must stay isolated. Before the fix, Python's
        late-binding closures could make every period report the *last*
        period's values instead of its own."""
        current = [{"id": "assets", "balance": 100.0, "children": []}]
        periods = [
            {"label": "Jan", "date_to": "2024-01-31", "date_from": "2024-01-01",
             "lines": [{"id": "assets", "balance": 10.0, "children": []}]},
            {"label": "Feb", "date_to": "2024-02-29", "date_from": "2024-02-01",
             "lines": [{"id": "assets", "balance": 20.0, "children": []}]},
            {"label": "Mar", "date_to": "2024-03-31", "date_from": "2024-03-01",
             "lines": [{"id": "assets", "balance": 30.0, "children": []}]},
        ]
        merged = self.engine.merge_multi_comparison_lines(current, periods)
        balances = [cb["balance"] for cb in merged[0]["comparison_balances"]]
        labels = [cb["label"] for cb in merged[0]["comparison_balances"]]
        self.assertEqual(balances, [10.0, 20.0, 30.0])
        self.assertEqual(labels, ["Jan", "Feb", "Mar"])
        # first comparison column also mirrored onto comparison_balance
        self.assertEqual(merged[0]["comparison_balance"], 10.0)

    def test_merge_multi_comparison_lines_empty_periods(self):
        current = [{"id": "assets", "balance": 100.0, "children": []}]
        merged = self.engine.merge_multi_comparison_lines(current, [])
        self.assertEqual(merged[0]["comparison_balances"], [])

    # ------------------------------------------------------------------
    # _rollup_balance / _collect_account_ids
    # ------------------------------------------------------------------

    def test_rollup_balance_sums_children_recursively(self):
        line = {
            "id": "assets", "balance": 0, "children": [
                {"id": "a", "balance": 100.0, "children": []},
                {"id": "b", "balance": 0, "children": [
                    {"id": "b1", "balance": 25.0, "children": []},
                    {"id": "b2", "balance": 75.0, "children": []},
                ]},
            ],
        }
        total = self.engine._rollup_balance(line)
        self.assertEqual(total, 200.0)
        self.assertEqual(line["balance"], 200.0)

    def test_collect_account_ids_unions_descendant_leaves(self):
        """Clicking a header/group total should drill down into every
        account underneath it (see the docstring in the engine)."""
        line = {
            "id": "assets", "children": [
                {"id": "cash", "account_id": 11, "children": []},
                {"id": "recv_group", "children": [
                    {"id": "recv", "account_id": 22, "children": []},
                ]},
            ],
        }
        ids = self.engine._collect_account_ids(line)
        self.assertEqual(set(ids), {11, 22})
        self.assertEqual(set(line["account_ids"]), {11, 22})

    def test_display_sign_conventions(self):
        """Assets/expenses keep their natural debit balance; liabilities/
        income are flipped so the report always shows a positive number
        for a normal credit balance."""
        self.assertEqual(self.engine._display_asset(500.0), 500.0)
        self.assertEqual(self.engine._display_expense(500.0), 500.0)
        # liability/income natural balance is a *credit*, i.e. raw = -500
        self.assertEqual(self.engine._display_liability(-500.0), 500.0)
        self.assertEqual(self.engine._display_income(-500.0), 500.0)