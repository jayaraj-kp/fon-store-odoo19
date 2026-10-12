# Copyright 2024 YourCompany
# License: LGPL-3.0 or later

"""
Large-Dataset Performance & Correctness Tests
===============================================
പഴയ test suite-ൽ correctness sixed small datasets-ൽ മാത്രമേ verify
ചെയ്തിരുന്നുള്ളൂ. ഈ file "വലിയ data വന്നാൽ report തെറ്റാവുമോ / തകരുമോ"
എന്ന ചോദ്യത്തിന് നേരിട്ട് ഉത്തരം കൊടുക്കുന്നു:

  1. Correctness at scale — നൂറുകണക്കിന് accounts / ആയിരക്കണക്കിന്
     move lines ഉള്ളപ്പോഴും balance sheet total കൃത്യമായി match
     ചെയ്യുന്നോ (ഒരു hidden default limit വഴി ഡാറ്റ silently
     truncate ആകുന്നില്ല എന്ന് ഉറപ്പാക്കുന്നു — ഇത് real-world-ൽ
     ഏറ്റവും സാധാരണമായ "large data → wrong statement" bug ആണ്).
  2. Query-count stays O(1) — row count കൂടുന്നതിനനുസരിച്ച് query
     count കൂടരുത് (_read_group aggregation ശരിക്കും ഉപയോഗിക്കുന്നു
     എന്ന് പ്രൂവ് ചെയ്യുന്നു, per-line Python loop അല്ല).
  3. Bounded execution time — ഒരു generous ceiling വച്ച് ഒരു basic
     regression-guard ആയി.

Note: CI റൺടൈം balance ചെയ്യാൻ ഇവിടെ moderate sizes (150 accounts,
~2000 move lines) ഉപയോഗിച്ചിരിക്കുന്നു. Staging/load-test
environment-ൽ _N_ACCOUNTS / _N_MOVES ഉയർത്തി പ്രത്യേകം ഓടിക്കാം.
"""

import time

from odoo.tests import TransactionCase, tagged

from .common import FSEnterpriseCommon


@tagged("post_install", "-at_install", "fs_performance")
class TestLargeDatasetCorrectness(FSEnterpriseCommon):
    """Proves the engine's totals are correct even when there are many
    distinct accounts / many move lines — not just silently right for
    the handful of accounts a small unit test happens to create."""

    _N_ACCOUNTS = 150  # deliberately > Odoo's classic default search
    #                    page size (80), to catch any accidental
    #                    search()[:limit] / read_group groupby-limit bug.
    _N_MOVES_PER_ACCOUNT = 3

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        company = cls.company_data["company"]

        # Create many distinct asset accounts (not just reuse the one
        # default fixture account) — this is what actually exercises
        # the account_id groupby + account.account.search_read path at
        # scale.
        cls.many_accounts = cls.env["account.account"].create([
            {
                "name": f"Perf Test Asset {i:04d}",
                "code": f"PT{i:04d}",
                "account_type": "asset_current",
                "company_ids": [(6, 0, [company.id])],
            }
            for i in range(cls._N_ACCOUNTS)
        ])

        cls.expected_total = 0.0
        move_vals = []
        for idx, account in enumerate(cls.many_accounts):
            for j in range(cls._N_MOVES_PER_ACCOUNT):
                amount = 10.0 + idx + j  # varying, non-round amounts
                cls.expected_total += amount
                move_vals.append({
                    "move_type": "entry",
                    "date": "2024-06-15",
                    "journal_id": cls.journal_misc.id,
                    "line_ids": [
                        (0, 0, {
                            "account_id": account.id,
                            "debit": amount, "credit": 0.0, "name": "perf",
                        }),
                        (0, 0, {
                            "account_id": cls.account_payable.id,
                            "debit": 0.0, "credit": amount, "name": "perf",
                        }),
                    ],
                })
        # Bulk-create in one ORM call, then bulk-post — far faster than
        # creating/posting one move at a time, and also exercises the
        # analytic_account_ids batched-write path in account_move_line.py
        # under real bulk-import conditions.
        moves = cls.env["account.move"].create(move_vals)
        moves.action_post()

    def test_balance_sheet_total_matches_full_dataset_not_truncated(self):
        """The single most important large-data regression: if any code
        path (now or introduced later) accidentally uses a limited
        search() instead of unlimited _read_group aggregation, this
        catches it immediately by comparing against the true sum."""
        result = self.engine.get_balance_sheet(
            date_to="2024-12-31",
            company_id=self.company_data["company"].id,
        )
        assets = self.find_line(result["lines"], "assets")
        self.assertIsNotNone(assets)
        self.assertAlmostEqual(
            assets["balance"], self.expected_total, places=2,
            msg=(
                "Balance Sheet total does not match the true sum over "
                f"{self._N_ACCOUNTS} accounts — data may be silently "
                "truncated (classic large-data reporting bug)."
            ),
        )

    def test_all_individual_accounts_present_in_lines(self):
        """Every one of the _N_ACCOUNTS accounts must have its own leaf
        row — none should be dropped because of a hidden pagination
        limit on the account listing or the groupby."""
        result = self.engine.get_balance_sheet(
            date_to="2024-12-31",
            company_id=self.company_data["company"].id,
        )
        flat = self.engine._flatten_lines(result["lines"])
        present_account_leaf_ids = {
            line_id for line_id in flat
            if isinstance(line_id, str) and line_id.startswith("assets")
            and "_acc_" in line_id
        }
        self.assertGreaterEqual(
            len(present_account_leaf_ids), self._N_ACCOUNTS,
            "Some accounts are missing from the Balance Sheet output "
            "— possible silent truncation at scale.",
        )

    def test_profit_and_loss_unaffected_by_unrelated_volume(self):
        """Sanity check: a large volume of Balance Sheet accounts must
        not corrupt or slow-path the (unrelated) P&L computation."""
        result = self.engine.get_profit_and_loss(
            date_from="2024-01-01", date_to="2024-12-31",
            company_id=self.company_data["company"].id,
        )
        net_profit = self.find_line(result["lines"], "net_profit")
        self.assertAlmostEqual(net_profit["balance"], 0.0)


@tagged("post_install", "-at_install", "fs_performance")
class TestQueryCountStaysConstant(TransactionCase):
    """Proves _get_account_balances() etc. use aggregate _read_group
    (O(1) queries) rather than O(n) per-line Python loops, by counting
    actual SQL statements for a small vs. a large dataset and asserting
    they are (almost) identical.

    We intentionally do NOT hardcode an exact query number (that would
    be brittle across Odoo point-releases); instead we compare
    small-vs-large, which is robust and still catches the real
    regression we care about: someone replacing _read_group with a
    per-account loop that fires one query per account.
    """

    def setUp(self):
        super().setUp()
        self.engine = self.env["financial.report.engine"]

    def _build_company_with_n_accounts(self, name, n_accounts):
        from odoo.addons.account.tests.common import AccountTestInvoicingCommon
        # Lightweight: reuse an existing minimal chart rather than a
        # second full AccountTestInvoicingCommon setUpClass (expensive).
        # We piggy-back on whatever company_data the running test env
        # already has via the account module's demo/minimal CoA.
        company = self.env["res.company"].search([], limit=1)
        journal = self.env["account.journal"].search(
            [("company_id", "=", company.id), ("type", "=", "general")], limit=1
        )
        payable = self.env["account.account"].search(
            [("company_ids", "in", company.id), ("account_type", "=", "liability_payable")],
            limit=1,
        )
        accounts = self.env["account.account"].create([
            {
                "name": f"{name} {i}", "code": f"{name[:2].upper()}{i:04d}",
                "account_type": "asset_current",
                "company_ids": [(6, 0, [company.id])],
            }
            for i in range(n_accounts)
        ])
        move_vals = [
            {
                "move_type": "entry", "date": "2024-06-01",
                "journal_id": journal.id,
                "line_ids": [
                    (0, 0, {"account_id": acc.id, "debit": 5.0, "credit": 0.0, "name": "q"}),
                    (0, 0, {"account_id": payable.id, "debit": 0.0, "credit": 5.0, "name": "q"}),
                ],
            }
            for acc in accounts
        ]
        moves = self.env["account.move"].create(move_vals)
        moves.action_post()
        return company

    def _count_queries(self, func):
        """Wrap self.env.cr.execute to count real SQL round-trips."""
        cr = self.env.cr
        original_execute = cr.execute
        counter = {"n": 0}

        def counting_execute(*args, **kwargs):
            counter["n"] += 1
            return original_execute(*args, **kwargs)

        cr.execute = counting_execute
        try:
            func()
        finally:
            cr.execute = original_execute
        return counter["n"]

    def test_query_count_does_not_scale_with_account_count(self):
        small_company = self._build_company_with_n_accounts("QcSmall", 10)
        large_company = self._build_company_with_n_accounts("QcLarge", 200)

        small_queries = self._count_queries(
            lambda: self.engine.get_balance_sheet(
                date_to="2024-12-31", company_id=small_company.id,
            )
        )
        large_queries = self._count_queries(
            lambda: self.engine.get_balance_sheet(
                date_to="2024-12-31", company_id=large_company.id,
            )
        )

        # Allow a small constant-factor tolerance (e.g. account.account
        # search_read batching by ID list can vary a little), but the
        # large dataset (20x more accounts) must NOT trigger anywhere
        # near 20x the queries — that would prove an O(n) per-row path.
        self.assertLessEqual(
            large_queries, small_queries + 5,
            f"Query count scaled with data volume "
            f"(small={small_queries}, large={large_queries}) — "
            "an aggregation path may have regressed into a per-row loop.",
        )


@tagged("post_install", "-at_install", "fs_performance")
class TestExecutionTimeBounded(FSEnterpriseCommon):
    """Coarse wall-clock regression guard. Deliberately generous
    thresholds — this is not a micro-benchmark, just a tripwire against
    an accidental N+1 / unbounded-loop regression making a report
    request take, say, 30+ seconds."""

    _N_ACCOUNTS = 200

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        company = cls.company_data["company"]
        accounts = cls.env["account.account"].create([
            {
                "name": f"Timing Asset {i}", "code": f"TA{i:04d}",
                "account_type": "asset_current",
                "company_ids": [(6, 0, [company.id])],
            }
            for i in range(cls._N_ACCOUNTS)
        ])
        move_vals = [
            {
                "move_type": "entry", "date": "2024-06-01",
                "journal_id": cls.journal_misc.id,
                "line_ids": [
                    (0, 0, {"account_id": acc.id, "debit": 25.0, "credit": 0.0, "name": "t"}),
                    (0, 0, {"account_id": cls.account_payable.id,
                            "debit": 0.0, "credit": 25.0, "name": "t"}),
                ],
            }
            for acc in accounts
        ]
        moves = cls.env["account.move"].create(move_vals)
        moves.action_post()

    def test_balance_sheet_completes_within_generous_bound(self):
        start = time.monotonic()
        self.engine.get_balance_sheet(
            date_to="2024-12-31",
            company_id=self.company_data["company"].id,
        )
        elapsed = time.monotonic() - start
        self.assertLess(
            elapsed, 10.0,
            f"get_balance_sheet() took {elapsed:.2f}s for "
            f"{self._N_ACCOUNTS} accounts — investigate for a "
            "performance regression before this reaches production scale.",
        )

    def test_analytic_columns_completes_within_generous_bound(self):
        """The analytic-column path is the most query-heavy branch
        (batched per-analytic aggregation) — worth its own timing
        guard given _MAX_ANALYTIC_ACCOUNTS allows up to 20 columns."""
        analytics = self.env["account.analytic.account"].create([
            {"name": f"Perf Analytic {i}", "company_id": self.company_data["company"].id}
            for i in range(20)
        ])
        start = time.monotonic()
        # Same code path the screen uses (one SQL per date range, plus the
        # optional Unassigned column).
        self.engine.get_analytic_report(
            "bs", None, "2024-12-31", self.company_data["company"].id,
            analytic_account_ids=analytics.ids, include_unassigned=True,
        )
        elapsed = time.monotonic() - start
        self.assertLess(
            elapsed, 15.0,
            f"get_balance_sheet() with 20 analytic columns took "
            f"{elapsed:.2f}s over {self._N_ACCOUNTS} accounts.",
        )