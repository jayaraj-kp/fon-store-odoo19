# License: LGPL-3.0 or later
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo import fields


@tagged("post_install", "-at_install")
class TestComputeEnterpriseGLData(TransactionCase):
    """Unit tests for compute_enterprise_gl_data function."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.currency = cls.company.currency_id

        # Create test accounts
        cls.account_receivable = cls.env["account.account"].create({
            "code": "1000",
            "name": "Accounts Receivable",
            "account_type": "asset_receivable",
            "company_ids": [(6, 0, [cls.company.id])],
        })
        cls.account_payable = cls.env["account.account"].create({
            "code": "2000",
            "name": "Accounts Payable",
            "account_type": "liability_payable",
            "company_ids": [(6, 0, [cls.company.id])],
        })
        cls.account_revenue = cls.env["account.account"].create({
            "code": "4000",
            "name": "Revenue",
            "account_type": "income",
            "company_ids": [(6, 0, [cls.company.id])],
        })
        cls.account_expense = cls.env["account.account"].create({
            "code": "5000",
            "name": "Expense",
            "account_type": "expense",
            "company_ids": [(6, 0, [cls.company.id])],
        })

        # Create test journals
        cls.journal_sale = cls.env["account.journal"].create({
            "name": "Sales Journal",
            "code": "SALE",
            "type": "sale",
            "company_id": cls.company.id,
        })
        cls.journal_purchase = cls.env["account.journal"].create({
            "name": "Purchase Journal",
            "code": "PUR",
            "type": "purchase",
            "company_id": cls.company.id,
        })
        cls.journal_general = cls.env["account.journal"].create({
            "name": "General Journal",
            "code": "GEN",
            "type": "general",
            "company_id": cls.company.id,
        })

        # Create test partners
        cls.partner_a = cls.env["res.partner"].create({
            "name": "Partner A",
        })
        cls.partner_b = cls.env["res.partner"].create({
            "name": "Partner B",
        })

        # Create test moves
        cls._create_test_moves()

    @classmethod
    def _create_test_moves(cls):
        """Create test journal entries for testing."""
        move_vals_list = [
            # Posted move - Revenue
            {
                "date": "2024-01-15",
                "journal_id": cls.journal_sale.id,
                "move_type": "entry",
                "line_ids": [
                    (0, 0, {
                        "account_id": cls.account_receivable.id,
                        "partner_id": cls.partner_a.id,
                        "debit": 1000.0,
                        "credit": 0.0,
                    }),
                    (0, 0, {
                        "account_id": cls.account_revenue.id,
                        "debit": 0.0,
                        "credit": 1000.0,
                    }),
                ],
            },
            # Posted move - Expense
            {
                "date": "2024-01-20",
                "journal_id": cls.journal_purchase.id,
                "move_type": "entry",
                "line_ids": [
                    (0, 0, {
                        "account_id": cls.account_expense.id,
                        "partner_id": cls.partner_b.id,
                        "debit": 500.0,
                        "credit": 0.0,
                    }),
                    (0, 0, {
                        "account_id": cls.account_payable.id,
                        "partner_id": cls.partner_b.id,
                        "debit": 0.0,
                        "credit": 500.0,
                    }),
                ],
            },
            # Draft move (should be excluded by default)
            {
                "date": "2024-01-25",
                "journal_id": cls.journal_general.id,
                "move_type": "entry",
                "state": "draft",
                "line_ids": [
                    (0, 0, {
                        "account_id": cls.account_revenue.id,
                        "debit": 200.0,
                        "credit": 0.0,
                    }),
                    (0, 0, {
                        "account_id": cls.account_expense.id,
                        "debit": 0.0,
                        "credit": 200.0,
                    }),
                ],
            },
            # Cancelled move (should be excluded in all modes)
            {
                "date": "2024-01-28",
                "journal_id": cls.journal_general.id,
                "move_type": "entry",
                "state": "cancel",
                "line_ids": [
                    (0, 0, {
                        "account_id": cls.account_receivable.id,
                        "partner_id": cls.partner_a.id,
                        "debit": 999.0,
                        "credit": 0.0,
                    }),
                    (0, 0, {
                        "account_id": cls.account_revenue.id,
                        "debit": 0.0,
                        "credit": 999.0,
                    }),
                ],
            },
        ]
        for vals in move_vals_list:
            move = cls.env["account.move"].create(vals)
            if vals.get("state") == "cancel":
                move.button_cancel()
            elif vals.get("state") != "draft":
                move.action_post()

    def _call_compute(self, **kwargs):
        """Helper to call compute_enterprise_gl_data with defaults."""
        from general_ledger_enterprise_view.controllers.main import compute_enterprise_gl_data
        defaults = {
            "env": self.env,
            "date_from": "2024-01-01",
            "date_to": "2024-01-31",
            "company_id": self.company.id,
            "target_move": "posted",
            "report_type": "gl",
        }
        defaults.update(kwargs)
        return compute_enterprise_gl_data(**defaults)

    def test_basic_gl_computation(self):
        """Test basic GL computation with posted moves only."""
        result = self._call_compute()
        self.assertIn("accounts", result)
        self.assertEqual(len(result["accounts"]), 4)  # 4 accounts created

        # Find receivable account
        recv_acc = next(a for a in result["accounts"] if a["code"] == "1000")
        self.assertEqual(recv_acc["fin_bal"]["debit"], 1000.0)
        self.assertEqual(recv_acc["fin_bal"]["credit"], 0.0)
        self.assertEqual(recv_acc["fin_bal"]["ending_balance"], 1000.0)

        # Find revenue account
        rev_acc = next(a for a in result["accounts"] if a["code"] == "4000")
        self.assertEqual(rev_acc["fin_bal"]["debit"], 0.0)
        self.assertEqual(rev_acc["fin_bal"]["credit"], 1000.0)
        self.assertEqual(rev_acc["fin_bal"]["ending_balance"], -1000.0)

    def test_cancelled_moves_excluded(self):
        """Test that cancelled moves are excluded in all target_move modes."""
        # With target_move="all", cancelled should still be excluded
        result = self._call_compute(target_move="all")
        recv_acc = next(a for a in result["accounts"] if a["code"] == "1000")
        # Should only have the 1000 from posted move, not 999 from cancelled
        self.assertEqual(recv_acc["fin_bal"]["debit"], 1000.0)

    def test_draft_moves_included_with_target_move_all(self):
        """Test that draft moves are included when target_move='all'."""
        result = self._call_compute(target_move="all")
        rev_acc = next(a for a in result["accounts"] if a["code"] == "4000")
        # Should have 1000 (posted) + 200 (draft) = 1200 credit
        self.assertEqual(rev_acc["fin_bal"]["credit"], 1200.0)

    def test_draft_moves_excluded_with_target_move_posted(self):
        """Test that draft moves are excluded when target_move='posted' (default)."""
        result = self._call_compute(target_move="posted")
        rev_acc = next(a for a in result["accounts"] if a["code"] == "4000")
        # Should only have 1000 from posted move
        self.assertEqual(rev_acc["fin_bal"]["credit"], 1000.0)

    def test_partner_grouping_receivable(self):
        """Test partner grouping for receivable accounts."""
        result = self._call_compute(report_type="tb", grouped_by="partners")
        recv_acc = next(a for a in result["accounts"] if a["code"] == "1000")
        self.assertTrue(recv_acc["has_partners"])
        self.assertEqual(len(recv_acc["partner_groups"]), 1)
        pg = recv_acc["partner_groups"][0]
        self.assertEqual(pg["partner_id"], self.partner_a.id)
        self.assertEqual(pg["fin_bal"]["ending_balance"], 1000.0)

    def test_partner_grouping_payable(self):
        """Test partner grouping for payable accounts."""
        result = self._call_compute(report_type="tb", grouped_by="partners")
        pay_acc = next(a for a in result["accounts"] if a["code"] == "2000")
        self.assertTrue(pay_acc["has_partners"])
        self.assertEqual(len(pay_acc["partner_groups"]), 1)
        pg = pay_acc["partner_groups"][0]
        self.assertEqual(pg["partner_id"], self.partner_b.id)
        self.assertEqual(pg["fin_bal"]["ending_balance"], -500.0)

    def test_journal_grouping(self):
        """Test journal grouping when grouped_by='journals'."""
        result = self._call_compute(grouped_by="journals")
        recv_acc = next(a for a in result["accounts"] if a["code"] == "1000")
        self.assertTrue(recv_acc["has_journals"])
        self.assertEqual(len(recv_acc["journal_groups"]), 1)
        jg = recv_acc["journal_groups"][0]
        self.assertEqual(jg["journal_id"], self.journal_sale.id)
        self.assertEqual(jg["fin_bal"]["debit"], 1000.0)

    def test_hide_account_at_zero(self):
        """Test hide_account_at_0 filter."""
        # Create account with no moves
        empty_acc = self.env["account.account"].create({
            "code": "9999",
            "name": "Empty Account",
            "account_type": "asset_current",
            "company_ids": [(6, 0, [self.company.id])],
        })

        # Without hide_account_at_0
        result = self._call_compute(hide_account_at_0=False)
        self.assertTrue(any(a["code"] == "9999" for a in result["accounts"]))

        # With hide_account_at_0
        result = self._call_compute(hide_account_at_0=True)
        self.assertFalse(any(a["code"] == "9999" for a in result["accounts"]))

    def test_date_filtering(self):
        """Test date_from and date_to filtering."""
        # Create a move in February (outside Jan range)
        move = self.env["account.move"].create({
            "date": "2024-02-15",
            "journal_id": self.journal_general.id,
            "move_type": "entry",
            "line_ids": [
                (0, 0, {"account_id": self.account_revenue.id, "debit": 300.0, "credit": 0.0}),
                (0, 0, {"account_id": self.account_expense.id, "debit": 0.0, "credit": 300.0}),
            ],
        })
        move.action_post()

        # Query only January
        result = self._call_compute(date_from="2024-01-01", date_to="2024-01-31")
        rev_acc = next(a for a in result["accounts"] if a["code"] == "4000")
        self.assertEqual(rev_acc["fin_bal"]["credit"], 1000.0)  # Only Jan move

        # Query February
        result = self._call_compute(date_from="2024-02-01", date_to="2024-02-28")
        rev_acc = next(a for a in result["accounts"] if a["code"] == "4000")
        self.assertEqual(rev_acc["fin_bal"]["credit"], 300.0)  # Only Feb move

    def test_account_filter(self):
        """Test filtering by specific account_ids."""
        result = self._call_compute(account_ids=[self.account_receivable.id])
        self.assertEqual(len(result["accounts"]), 1)
        self.assertEqual(result["accounts"][0]["code"], "1000")

    def test_journal_filter(self):
        """Test filtering by specific journal_ids."""
        result = self._call_compute(journal_ids=[self.journal_sale.id])
        # Only sale journal moves
        recv_acc = next(a for a in result["accounts"] if a["code"] == "1000")
        self.assertEqual(recv_acc["fin_bal"]["debit"], 1000.0)
        rev_acc = next(a for a in result["accounts"] if a["code"] == "4000")
        self.assertEqual(rev_acc["fin_bal"]["credit"], 1000.0)
        # Expense and payable should not appear (no sale journal moves)
        self.assertFalse(any(a["code"] == "5000" for a in result["accounts"]))

    def test_currency_rounding(self):
        """Test that currency rounding is applied correctly."""
        # Create move with amounts requiring rounding
        move = self.env["account.move"].create({
            "date": "2024-01-10",
            "journal_id": self.journal_general.id,
            "move_type": "entry",
            "line_ids": [
                (0, 0, {"account_id": self.account_revenue.id, "debit": 100.123456, "credit": 0.0}),
                (0, 0, {"account_id": self.account_expense.id, "debit": 0.0, "credit": 100.123456}),
            ],
        })
        move.action_post()

        result = self._call_compute()
        rev_acc = next(a for a in result["accounts"] if a["code"] == "4000")
        # Should be rounded to currency precision (typically 2 decimals)
        self.assertEqual(rev_acc["fin_bal"]["debit"], round(100.123456, self.currency.decimal_places))

    def test_initial_balance_computation(self):
        """Test that initial balances (before date_from) are computed."""
        # Create a move in December 2023 (before date_from)
        move = self.env["account.move"].create({
            "date": "2023-12-15",
            "journal_id": self.journal_general.id,
            "move_type": "entry",
            "line_ids": [
                (0, 0, {"account_id": self.account_receivable.id, "partner_id": self.partner_a.id, "debit": 200.0, "credit": 0.0}),
                (0, 0, {"account_id": self.account_revenue.id, "debit": 0.0, "credit": 200.0}),
            ],
        })
        move.action_post()

        result = self._call_compute(date_from="2024-01-01", date_to="2024-01-31")
        recv_acc = next(a for a in result["accounts"] if a["code"] == "1000")
        # Initial balance should include Dec 2023 move
        self.assertEqual(recv_acc["init_bal"]["balance"], 200.0)
        # Ending balance = initial + period = 200 + 1000 = 1200
        self.assertEqual(recv_acc["fin_bal"]["ending_balance"], 1200.0)

    def test_initial_balance_cross_fiscal_year_balance_sheet(self):
        """Fix 1a: Balance-sheet accounts must carry their opening balance
        across ALL fiscal years, not just from fy_start.

        Regression: Before the fix, a move from 2022 would be ignored when
        running a 2024 report because init_domain only looked from fy_start
        (2024-01-01) onward. This caused wrong Trial Balance for any company
        with more than 1 year of data.
        """
        has_init_bal = "include_initial_balance" in self.env["account.account"]._fields
        if not has_init_bal:
            self.skipTest("include_initial_balance field not available — skipping cross-FY test")

        # Ensure the receivable account IS a balance-sheet account
        self.account_receivable.write({"include_initial_balance": True})

        # Move from TWO fiscal years ago (well before fy_start of the report)
        old_move = self.env["account.move"].create({
            "date": "2022-06-15",
            "journal_id": self.journal_general.id,
            "move_type": "entry",
            "line_ids": [
                (0, 0, {"account_id": self.account_receivable.id, "partner_id": self.partner_a.id, "debit": 5000.0, "credit": 0.0}),
                (0, 0, {"account_id": self.account_revenue.id, "debit": 0.0, "credit": 5000.0}),
            ],
        })
        old_move.action_post()

        # Run report for Jan 2024 — FY start would be 2024-01-01
        result = self._call_compute(date_from="2024-01-01", date_to="2024-01-31")

        # Balance-sheet account (receivable) must include the 2022 move in opening
        recv_acc = next((a for a in result["accounts"] if a["code"] == "1000"), None)
        self.assertIsNotNone(recv_acc, "Receivable account must appear in result")
        self.assertGreaterEqual(
            recv_acc["init_bal"]["balance"], 5000.0,
            "Balance-sheet opening balance must include transactions from previous fiscal years"
        )

    def test_initial_balance_cross_fiscal_year_pl_excluded(self):
        """Fix 1a: P&L accounts must NOT include prior-FY transactions in opening.

        Revenue/Expense accounts reset at the fiscal year start — they should
        only show opening from fy_start to date_from, not from all history.
        """
        has_init_bal = "include_initial_balance" in self.env["account.account"]._fields
        if not has_init_bal:
            self.skipTest("include_initial_balance field not available — skipping cross-FY test")

        # Ensure the revenue account is a P&L account
        self.account_revenue.write({"include_initial_balance": False})

        # Move from two fiscal years ago
        old_move = self.env["account.move"].create({
            "date": "2022-06-15",
            "journal_id": self.journal_general.id,
            "move_type": "entry",
            "line_ids": [
                (0, 0, {"account_id": self.account_receivable.id, "debit": 3000.0, "credit": 0.0}),
                (0, 0, {"account_id": self.account_revenue.id, "debit": 0.0, "credit": 3000.0}),
            ],
        })
        old_move.action_post()

        # Run report for Jan 2024 — FY start would be 2024-01-01
        result = self._call_compute(date_from="2024-01-01", date_to="2024-01-31")

        # P&L account (revenue) must NOT include the 2022 move in opening balance
        rev_acc = next((a for a in result["accounts"] if a["code"] == "4000"), None)
        if rev_acc:
            # No 2024 P&L transactions before Jan 1 → opening must be 0
            self.assertEqual(
                rev_acc["init_bal"]["balance"], 0.0,
                "P&L opening balance must NOT include prior fiscal year transactions"
            )

    def test_invalid_grouped_by_fallback(self):
        """Test that invalid grouped_by falls back to 'none'."""
        result = self._call_compute(grouped_by="invalid_value")
        # Should not crash, should fallback to 'none'
        self.assertIn("accounts", result)
        # No partner/journal groups should be present
        for acc in result["accounts"]:
            self.assertFalse(acc.get("has_partners"))
            self.assertFalse(acc.get("has_journals"))

    def test_multi_company_isolation(self):
        """Test that data from other companies is not included."""
        # Create another company
        other_company = self.env["res.company"].create({"name": "Other Company"})
        other_account = self.env["account.account"].create({
            "code": "9999",
            "name": "Other Account",
            "account_type": "asset_current",
            "company_ids": [(6, 0, [other_company.id])],
        })
        other_journal = self.env["account.journal"].create({
            "name": "Other Journal",
            "code": "OTH",
            "type": "general",
            "company_id": other_company.id,
        })
        move = self.env["account.move"].create({
            "date": "2024-01-15",
            "journal_id": other_journal.id,
            "move_type": "entry",
            "line_ids": [
                (0, 0, {"account_id": other_account.id, "debit": 100.0, "credit": 0.0}),
                (0, 0, {"account_id": self.account_expense.id, "debit": 0.0, "credit": 100.0}),
            ],
        })
        move.action_post()

        # Query with own company - should not see other company's account
        result = self._call_compute(company_id=self.company.id)
        self.assertFalse(any(a["code"] == "9999" for a in result["accounts"]))

    def test_analytic_filtering(self):
        """Test analytic account filtering."""
        analytic = self.env["account.analytic.account"].create({
            "name": "Test Analytic",
            "company_id": self.company.id,
        })

        # Create move with analytic distribution
        move = self.env["account.move"].create({
            "date": "2024-01-10",
            "journal_id": self.journal_general.id,
            "move_type": "entry",
            "line_ids": [
                (0, 0, {
                    "account_id": self.account_revenue.id,
                    "debit": 500.0,
                    "credit": 0.0,
                    "analytic_distribution": {str(analytic.id): 100},
                }),
                (0, 0, {
                    "account_id": self.account_expense.id,
                    "debit": 0.0,
                    "credit": 500.0,
                }),
            ],
        })
        move.action_post()

        # Filter by analytic
        result = self._call_compute(analytic_ids=[analytic.id])
        rev_acc = next(a for a in result["accounts"] if a["code"] == "4000")
        self.assertEqual(rev_acc["fin_bal"]["debit"], 500.0)

        # Without analytic filter, should see all
        result = self._call_compute()
        rev_acc = next(a for a in result["accounts"] if a["code"] == "4000")
        self.assertEqual(rev_acc["fin_bal"]["debit"], 1500.0)  # 1000 + 500

    def test_golden_master_include_lines_true_vs_false(self):
        """Golden-master: totals with include_lines=False must equal include_lines=True.

        This is the critical regression test for the SQL aggregation path.
        Both paths must produce identical account totals (init_bal, fin_bal,
        ending_balance) and identical partner group totals.
        """
        # Create additional moves for richer test data
        for i in range(5):
            move = self.env["account.move"].create({
                "date": "2024-01-%02d" % (10 + i),
                "journal_id": self.journal_general.id,
                "move_type": "entry",
                "line_ids": [
                    (0, 0, {
                        "account_id": self.account_receivable.id,
                        "partner_id": self.partner_a.id,
                        "debit": 200.0,
                        "credit": 0.0,
                    }),
                    (0, 0, {
                        "account_id": self.account_revenue.id,
                        "debit": 0.0,
                        "credit": 200.0,
                    }),
                ],
            })
            move.action_post()

        result_with = self._call_compute(include_lines=True)
        result_without = self._call_compute(include_lines=False)

        with_by_id = {a["id"]: a for a in result_with["accounts"]}
        without_by_id = {a["id"]: a for a in result_without["accounts"]}

        self.assertEqual(
            set(with_by_id.keys()),
            set(without_by_id.keys()),
            "Account sets must be identical between include_lines=True and False",
        )

        for acc_id in with_by_id:
            a_with = with_by_id[acc_id]
            a_without = without_by_id[acc_id]

            # init_bal must be identical
            self.assertEqual(
                a_with["init_bal"]["balance"],
                a_without["init_bal"]["balance"],
                "init_bal mismatch for account %s" % acc_id,
            )

            # fin_bal must be identical
            self.assertEqual(
                a_with["fin_bal"]["debit"],
                a_without["fin_bal"]["debit"],
                "fin_bal.debit mismatch for account %s" % acc_id,
            )
            self.assertEqual(
                a_with["fin_bal"]["credit"],
                a_without["fin_bal"]["credit"],
                "fin_bal.credit mismatch for account %s" % acc_id,
            )
            self.assertEqual(
                a_with["fin_bal"]["ending_balance"],
                a_without["fin_bal"]["ending_balance"],
                "fin_bal.ending_balance mismatch for account %s" % acc_id,
            )

            # Partner group totals must be identical
            pg_with = {pg["partner_id"]: pg for pg in a_with.get("partner_groups", [])}
            pg_without = {pg["partner_id"]: pg for pg in a_without.get("partner_groups", [])}
            self.assertEqual(set(pg_with.keys()), set(pg_without.keys()))
            for pid in pg_with:
                self.assertEqual(
                    pg_with[pid]["fin_bal"]["debit"],
                    pg_without[pid]["fin_bal"]["debit"],
                    "partner group debit mismatch",
                )
                self.assertEqual(
                    pg_with[pid]["fin_bal"]["credit"],
                    pg_without[pid]["fin_bal"]["credit"],
                    "partner group credit mismatch",
                )
                self.assertEqual(
                    pg_with[pid]["fin_bal"]["ending_balance"],
                    pg_without[pid]["fin_bal"]["ending_balance"],
                    "partner group ending_balance mismatch",
                )

    def test_include_lines_false_no_move_lines_in_response(self):
        """When include_lines=False, response must contain no move lines."""
        result = self._call_compute(include_lines=False)
        for acc in result["accounts"]:
            self.assertEqual(acc["move_lines"], [])
            for pg in acc.get("partner_groups", []):
                self.assertEqual(pg["move_lines"], [])

    def test_include_lines_true_has_move_lines(self):
        """When include_lines=True (default), move lines must be present."""
        result = self._call_compute(include_lines=True)
        # At least one account should have move lines
        has_lines = any(acc["move_lines"] for acc in result["accounts"])
        self.assertTrue(has_lines, "include_lines=True should include move lines")

    def test_pagination_running_balance_continuity(self):
        """Running balance must be continuous across pages."""
        from general_ledger_enterprise_view.controllers.main import _get_move_lines_page

        # Create 5 moves for receivable account
        for i in range(5):
            move = self.env["account.move"].create({
                "date": "2024-01-%02d" % (10 + i),
                "journal_id": self.journal_general.id,
                "move_type": "entry",
                "line_ids": [
                    (0, 0, {
                        "account_id": self.account_receivable.id,
                        "partner_id": self.partner_a.id,
                        "debit": 100.0,
                        "credit": 0.0,
                    }),
                    (0, 0, {
                        "account_id": self.account_revenue.id,
                        "debit": 0.0,
                        "credit": 100.0,
                    }),
                ],
            })
            move.action_post()

        domain = [
            ("company_id", "=", self.company.id),
            ("parent_state", "=", "posted"),
            ("date", ">=", "2024-01-01"),
            ("date", "<=", "2024-01-31"),
        ]

        # Get all lines via pagination
        all_lines = []
        last_id = 0
        while True:
            page = _get_move_lines_page(
                self.env, domain, self.account_receivable.id,
                page_size=3, last_id=last_id, currency=self.currency,
            )
            all_lines.extend(page["lines"])
            if not page["has_more"]:
                break
            last_id = page["last_id"]

        # Verify running balance continuity
        for i in range(1, len(all_lines)):
            prev_balance = all_lines[i - 1]["balance"]
            curr = all_lines[i]
            expected = self.currency.round(
                prev_balance + curr["debit"] - curr["credit"]
            )
            self.assertEqual(
                curr["balance"],
                expected,
                "Running balance discontinuity at line %d" % i,
            )

    def test_pagination_stable_ordering_same_date(self):
        """Lines with identical dates must be ordered by id (stable)."""
        from general_ledger_enterprise_view.controllers.main import _get_move_lines_page

        # Create multiple moves on the same date
        for i in range(5):
            move = self.env["account.move"].create({
                "date": "2024-01-15",
                "journal_id": self.journal_general.id,
                "move_type": "entry",
                "line_ids": [
                    (0, 0, {
                        "account_id": self.account_receivable.id,
                        "partner_id": self.partner_a.id,
                        "debit": 50.0,
                        "credit": 0.0,
                    }),
                    (0, 0, {
                        "account_id": self.account_revenue.id,
                        "debit": 0.0,
                        "credit": 50.0,
                    }),
                ],
            })
            move.action_post()

        domain = [
            ("company_id", "=", self.company.id),
            ("parent_state", "=", "posted"),
            ("date", ">=", "2024-01-01"),
            ("date", "<=", "2024-01-31"),
        ]

        result = _get_move_lines_page(
            self.env, domain, self.account_receivable.id,
            page_size=10, last_id=0, currency=self.currency,
        )

        # All lines have the same date, so they must be ordered by id
        for i in range(1, len(result["lines"])):
            self.assertLess(
                result["lines"][i - 1]["id"],
                result["lines"][i]["id"],
                "Lines with same date must be ordered by id",
            )

    def test_pagination_empty_result(self):
        """Empty account returns empty lines, no error."""
        from general_ledger_enterprise_view.controllers.main import _get_move_lines_page

        empty_acc = self.env["account.account"].create({
            "code": "9998",
            "name": "Empty Account",
            "account_type": "asset_current",
            "company_ids": [(6, 0, [self.company.id])],
        })

        domain = [
            ("company_id", "=", self.company.id),
            ("parent_state", "=", "posted"),
            ("date", ">=", "2024-01-01"),
            ("date", "<=", "2024-01-31"),
        ]

        result = _get_move_lines_page(
            self.env, domain, empty_acc.id,
            page_size=80, last_id=0, currency=self.currency,
        )
        self.assertEqual(result["lines"], [])
        self.assertEqual(result["balance_before"], 0.0)
        self.assertFalse(result["has_more"])

    def test_partner_without_opening_balance_lazy_mode(self):
        """A new partner created with transactions strictly in the current period (no opening balance)
        must appear in partner groups in both include_lines=True and include_lines=False (lazy mode),
        with valid partner names and matching figures."""
        new_partner = self.env["res.partner"].create({
            "name": "Brand New Partner",
        })

        move = self.env["account.move"].create({
            "date": "2024-01-25",
            "journal_id": self.journal_general.id,
            "move_type": "entry",
            "line_ids": [
                (0, 0, {
                    "account_id": self.account_receivable.id,
                    "partner_id": new_partner.id,
                    "debit": 450.0,
                    "credit": 0.0,
                }),
                (0, 0, {
                    "account_id": self.account_revenue.id,
                    "debit": 0.0,
                    "credit": 450.0,
                }),
            ],
        })
        move.action_post()

        result_with = self._call_compute(report_type="tb", include_lines=True)
        result_without = self._call_compute(report_type="tb", include_lines=False)

        rec_acc_with = next(a for a in result_with["accounts"] if a["id"] == self.account_receivable.id)
        rec_acc_without = next(a for a in result_without["accounts"] if a["id"] == self.account_receivable.id)

        pg_with = {pg["partner_id"]: pg for pg in rec_acc_with.get("partner_groups", [])}
        pg_without = {pg["partner_id"]: pg for pg in rec_acc_without.get("partner_groups", [])}

        self.assertIn(new_partner.id, pg_with, "New partner must be in partner_groups when include_lines=True")
        self.assertIn(new_partner.id, pg_without, "New partner must be in partner_groups when include_lines=False")

        self.assertEqual(pg_without[new_partner.id]["name"], "Brand New Partner")
        self.assertEqual(pg_without[new_partner.id]["fin_bal"]["debit"], 450.0)
        self.assertEqual(pg_without[new_partner.id]["fin_bal"]["ending_balance"], 450.0)
        self.assertEqual(
            pg_with[new_partner.id]["fin_bal"]["ending_balance"],
            pg_without[new_partner.id]["fin_bal"]["ending_balance"],
        )

    def test_trial_balance_unallocated_earnings_multi_year(self):
        """In a multi-year scenario with prior fiscal year transactions, the Trial Balance must
        include an Unallocated Earnings row with the net of prior P&L transactions, ensuring
        opening balance and ending balance sum to zero across all accounts."""
        # Create a prior year move in 2023 (before 2024 fiscal year)
        # Revenue credited 1200, Receivable debited 1200
        prior_move = self.env["account.move"].create({
            "date": "2023-06-15",
            "journal_id": self.journal_sale.id,
            "move_type": "entry",
            "line_ids": [
                (0, 0, {
                    "account_id": self.account_receivable.id,
                    "partner_id": self.partner_a.id,
                    "debit": 1200.0,
                    "credit": 0.0,
                }),
                (0, 0, {
                    "account_id": self.account_revenue.id,
                    "debit": 0.0,
                    "credit": 1200.0,
                }),
            ],
        })
        prior_move.action_post()

        # Compute TB for 2024
        result_tb = self._call_compute(report_type="tb", include_lines=False)
        accounts = result_tb["accounts"]

        # Check that synthetic Unallocated Earnings row exists
        ue_acc = next((a for a in accounts if a.get("id") == "unallocated_earnings"), None)
        self.assertIsNotNone(ue_acc, "Trial Balance must include synthetic Unallocated Earnings row")
        self.assertEqual(ue_acc["name"], "Unallocated Earnings")
        # In double-entry, credit balance for revenue rolls in as credit (negative balance: debit - credit = -1200)
        # Check initial balance and ending balance
        self.assertEqual(ue_acc["init_bal"]["balance"], -1200.0)
        self.assertEqual(ue_acc["fin_bal"]["ending_balance"], -1200.0)

        # Check total initial balance and total ending balance across all TB accounts sum to 0.0
        tot_init = sum(a["init_bal"]["balance"] for a in accounts)
        tot_end = sum(a["fin_bal"]["ending_balance"] for a in accounts)

        self.assertAlmostEqual(tot_init, 0.0, places=2, msg="TB initial balance across all accounts must tally to zero")
        self.assertAlmostEqual(tot_end, 0.0, places=2, msg="TB ending balance across all accounts must tally to zero")

        # In GL mode, Unallocated Earnings synthetic row must NOT be present
        result_gl = self._call_compute(report_type="gl", include_lines=False)
        gl_ue = next((a for a in result_gl["accounts"] if a.get("id") == "unallocated_earnings"), None)
        self.assertIsNone(gl_ue, "General Ledger must NOT contain synthetic Unallocated Earnings row")

    # ------------------------------------------------------------------
    # Row cap, hide-zero in lazy mode, archived partners, UE only when unfiltered
    # ------------------------------------------------------------------
    def test_row_cap_raises_user_error(self):
        """include_lines=True with more lines than max_lines -> UserError (not OOM)."""
        from odoo.exceptions import UserError
        # Fixture has 4 posted lines in Jan 2024.
        with self.assertRaises(UserError):
            self._call_compute(include_lines=True, max_lines=1)
        # Cap is irrelevant for the SQL-aggregated (lazy) path ...
        result = self._call_compute(include_lines=False, max_lines=1)
        self.assertIn("accounts", result)
        # ... and a generous cap does not interfere.
        result = self._call_compute(include_lines=True, max_lines=1000)
        self.assertTrue(result["accounts"])

    def test_hide_zero_keeps_account_with_netting_activity_lazy_and_eager(self):
        """Account with debit == credit in the period must stay visible with
        hide_account_at_0=True in BOTH modes (lazy mode has no lines_out)."""
        acc_net = self.env["account.account"].create({
            "code": "9100", "name": "Netting Account", "account_type": "asset_current",
            "company_ids": [(6, 0, [self.company.id])],
        })
        acc_counter = self.env["account.account"].create({
            "code": "9101", "name": "Netting Counter", "account_type": "asset_current",
            "company_ids": [(6, 0, [self.company.id])],
        })
        for date, d_net, c_net in (("2024-01-05", 100.0, 0.0), ("2024-01-06", 0.0, 100.0)):
            move = self.env["account.move"].create({
                "date": date,
                "journal_id": self.journal_general.id,
                "move_type": "entry",
                "line_ids": [
                    (0, 0, {"account_id": acc_net.id, "debit": d_net, "credit": c_net}),
                    (0, 0, {"account_id": acc_counter.id, "debit": c_net, "credit": d_net}),
                ],
            })
            move.action_post()
        for include_lines in (True, False):
            result = self._call_compute(hide_account_at_0=True, include_lines=include_lines)
            codes = [a["code"] for a in result["accounts"]]
            self.assertIn(
                "9100", codes,
                "Account with period activity netting to 0 hidden (include_lines=%s)" % include_lines,
            )

    def test_archived_partner_name_kept_in_lazy_tb(self):
        """Archived partners must keep their name (not 'Unknown Partner')."""
        partner = self.env["res.partner"].create({"name": "Archived Customer"})
        move = self.env["account.move"].create({
            "date": "2024-01-12",
            "journal_id": self.journal_general.id,
            "move_type": "entry",
            "line_ids": [
                (0, 0, {"account_id": self.account_receivable.id, "partner_id": partner.id,
                        "debit": 70.0, "credit": 0.0}),
                (0, 0, {"account_id": self.account_revenue.id, "debit": 0.0, "credit": 70.0}),
            ],
        })
        move.action_post()
        partner.active = False
        for include_lines in (True, False):
            result = self._call_compute(report_type="tb", include_lines=include_lines)
            rec = next(a for a in result["accounts"] if a["id"] == self.account_receivable.id)
            names = {pg["partner_id"]: pg["name"] for pg in rec["partner_groups"]}
            self.assertEqual(names.get(partner.id), "Archived Customer")

    def test_unallocated_earnings_only_for_unfiltered_tb(self):
        """UE row: present in unfiltered TB; absent in GL and in any filtered TB."""
        prior = self.env["account.move"].create({
            "date": "2023-06-15",
            "journal_id": self.journal_general.id,
            "move_type": "entry",
            "line_ids": [
                (0, 0, {"account_id": self.account_receivable.id, "partner_id": self.partner_a.id,
                        "debit": 800.0, "credit": 0.0}),
                (0, 0, {"account_id": self.account_revenue.id, "debit": 0.0, "credit": 800.0}),
            ],
        })
        prior.action_post()

        def has_ue(result):
            return any(a["id"] == "unallocated_earnings" for a in result["accounts"])

        self.assertTrue(has_ue(self._call_compute(report_type="tb", include_lines=False)))
        self.assertFalse(has_ue(self._call_compute(report_type="gl", include_lines=False)))
        self.assertFalse(has_ue(self._call_compute(
            report_type="tb", include_lines=False,
            account_ids=[self.account_receivable.id])))
        self.assertFalse(has_ue(self._call_compute(
            report_type="tb", include_lines=False,
            journal_ids=[self.journal_general.id])))


@tagged("post_install", "-at_install")
class TestExportFunctions(TransactionCase):
    """Tests for export functions."""

    def test_xlsx_export_gl(self):
        """Test XLSX export for General Ledger."""
        from general_ledger_enterprise_view.controllers.main import GeneralLedgerEnterpriseController
        ctrl = GeneralLedgerEnterpriseController()
        data = {
            "accounts": [
                {
                    "id": 1,
                    "code": "1000",
                    "name": "Test Account",
                    "account_type": "asset_receivable",
                    "init_bal": {"debit": 100.0, "credit": 0.0, "balance": 100.0},
                    "fin_bal": {"debit": 50.0, "credit": 25.0, "balance": 25.0, "ending_balance": 125.0},
                    "move_lines": [
                        {"id": 1, "date": "2024-01-15", "move_name": "MISC/001", "partner": "Partner A",
                         "debit": 50.0, "credit": 0.0, "balance": 150.0, "amount_currency": 0.0, "currency": "", "journal": "General", "ref_label": "Test"},
                    ],
                }
            ],
            "company_name": "Test Company",
            "date_from": "2024-01-01",
            "date_to": "2024-01-31",
        }
        filters = {"date_from": "2024-01-01", "date_to": "2024-01-31", "report_type": "gl"}
        result = ctrl._export_xlsx(self.env, "gl", data, filters)
        self.assertIn("file_content", result)
        self.assertIn("file_name", result)
        self.assertTrue(result["file_name"].endswith(".xlsx"))

    def test_xlsx_export_tb(self):
        """Test XLSX export for Trial Balance."""
        from general_ledger_enterprise_view.controllers.main import GeneralLedgerEnterpriseController
        ctrl = GeneralLedgerEnterpriseController()
        data = {
            "accounts": [
                {
                    "id": 1,
                    "code": "1000",
                    "name": "Test Account",
                    "account_type": "asset_receivable",
                    "init_bal": {"balance": 100.0},
                    "fin_bal": {"debit": 50.0, "credit": 25.0, "balance": 25.0, "ending_balance": 125.0},
                    "move_lines": [],
                    "has_partners": False,
                }
            ],
            "company_name": "Test Company",
            "date_from": "2024-01-01",
            "date_to": "2024-01-31",
        }
        filters = {"date_from": "2024-01-01", "date_to": "2024-01-31", "report_type": "tb"}
        result = ctrl._export_xlsx(self.env, "tb", data, filters)
        self.assertIn("file_content", result)
        self.assertIn("file_name", result)
        self.assertTrue(result["file_name"].endswith(".xlsx"))

    def test_pdf_export_gl(self):
        """Test PDF export for General Ledger (basic smoke test)."""
        from general_ledger_enterprise_view.controllers.main import GeneralLedgerEnterpriseController
        ctrl = GeneralLedgerEnterpriseController()
        data = {
            "accounts": [
                {
                    "id": 1,
                    "code": "1000",
                    "name": "Test Account",
                    "account_type": "asset_receivable",
                    "init_bal": {"debit": 100.0, "credit": 0.0, "balance": 100.0},
                    "fin_bal": {"debit": 50.0, "credit": 25.0, "balance": 25.0, "ending_balance": 125.0},
                    "move_lines": [],
                }
            ],
            "company_name": "Test Company",
            "date_from": "2024-01-01",
            "date_to": "2024-01-31",
            "currency_name": "USD",
            "currency_symbol": "$",
        }
        filters = {"date_from": "2024-01-01", "date_to": "2024-01-31", "report_type": "gl", "company_id": self.env.company.id}
        # This will fail if wkhtmltopdf not installed, but we can at least check it doesn't crash on data prep
        try:
            result = ctrl._export_pdf(self.env, "gl", data, filters)
            self.assertIn("file_content", result)
            self.assertIn("file_name", result)
            self.assertTrue(result["file_name"].endswith(".pdf"))
        except Exception as e:
            if "wkhtmltopdf" in str(e).lower():
                self.skipTest("wkhtmltopdf not installed")
            raise