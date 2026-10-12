# License: LGPL-3.0 or later
"""Tests for _get_move_lines_page keyset cursor and balance_before computation."""
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestKeysetAndBalanceBefore(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.currency = cls.company.currency_id

        cls.account_recv = cls.env["account.account"].create({
            "code": "1000",
            "name": "Receivable",
            "account_type": "asset_receivable",
            "company_ids": [(6, 0, [cls.company.id])],
        })
        cls.account_rev = cls.env["account.account"].create({
            "code": "4000",
            "name": "Revenue",
            "account_type": "income",
            "company_ids": [(6, 0, [cls.company.id])],
        })
        cls.journal = cls.env["account.journal"].create({
            "name": "Test",
            "code": "TST",
            "type": "general",
            "company_id": cls.company.id,
        })
        cls.partner = cls.env["res.partner"].create({"name": "P1"})

    def _domain(self):
        return [
            ("company_id", "=", self.company.id),
            ("parent_state", "=", "posted"),
            ("date", ">=", "2024-01-01"),
            ("date", "<=", "2024-01-31"),
        ]

    def test_backdated_entries_not_skipped(self):
        """Bug 1: back-dated entries must not be skipped by keyset cursor."""
        from odoo.addons.general_ledger_enterprise_view.controllers.main import _get_move_lines_page

        # Move A: Jan 15 (created first -> lower id)
        move_a = self.env["account.move"].create({
            "date": "2024-01-15",
            "journal_id": self.journal.id,
            "move_type": "entry",
            "line_ids": [
                (0, 0, {"account_id": self.account_recv.id, "partner_id": self.partner.id, "debit": 100.0, "credit": 0.0}),
                (0, 0, {"account_id": self.account_rev.id, "debit": 0.0, "credit": 100.0}),
            ],
        })
        move_a.action_post()

        # Move B: Jan 10 (created second -> higher id, but earlier date)
        move_b = self.env["account.move"].create({
            "date": "2024-01-10",
            "journal_id": self.journal.id,
            "move_type": "entry",
            "line_ids": [
                (0, 0, {"account_id": self.account_recv.id, "partner_id": self.partner.id, "debit": 200.0, "credit": 0.0}),
                (0, 0, {"account_id": self.account_rev.id, "debit": 0.0, "credit": 200.0}),
            ],
        })
        move_b.action_post()

        # Fetch all lines via pagination
        all_lines = []
        last_id = 0
        last_date = None
        while True:
            page = _get_move_lines_page(
                self.env, self._domain(), self.account_recv.id,
                page_size=1, last_id=last_id, last_date=last_date,
                currency=self.currency,
            )
            all_lines.extend(page["lines"])
            if not page["has_more"]:
                break
            last_id = page["last_id"]
            last_date = page["last_date"]

        # Must have BOTH lines
        self.assertEqual(
            len(all_lines), 2,
            "Back-dated entry was skipped! Got %d lines, expected 2." % len(all_lines),
        )

        # Verify order: Jan 10 first, then Jan 15
        dates = [l["date"] for l in all_lines]
        self.assertEqual(dates[0], "2024-01-10")
        self.assertEqual(dates[1], "2024-01-15")

    def test_balance_before_not_zero(self):
        """Bug 2: balance_before must reflect sum of prior lines."""
        from odoo.addons.general_ledger_enterprise_view.controllers.main import _get_move_lines_page

        for i in range(3):
            move = self.env["account.move"].create({
                "date": "2024-01-%02d" % (10 + i),
                "journal_id": self.journal.id,
                "move_type": "entry",
                "line_ids": [
                    (0, 0, {"account_id": self.account_recv.id, "partner_id": self.partner.id, "debit": 100.0, "credit": 0.0}),
                    (0, 0, {"account_id": self.account_rev.id, "debit": 0.0, "credit": 100.0}),
                ],
            })
            move.action_post()

        # First page: balance_before should be 0 (no prior lines)
        page1 = _get_move_lines_page(
            self.env, self._domain(), self.account_recv.id,
            page_size=1, last_id=0, currency=self.currency,
        )
        self.assertEqual(page1["balance_before"], 0.0)

        # Second page: balance_before should be 100 (one prior line)
        page2 = _get_move_lines_page(
            self.env, self._domain(), self.account_recv.id,
            page_size=1, last_id=page1["last_id"],
            last_date=page1["last_date"],
            currency=self.currency,
        )
        self.assertEqual(
            page2["balance_before"], 100.0,
            "balance_before should be 100.0 but got %s" % page2["balance_before"],
        )

    def test_balance_before_includes_opening(self):
        """Bug 2: opening balance must be included in balance_before."""
        from odoo.addons.general_ledger_enterprise_view.controllers.main import _get_move_lines_page

        # Opening move in Dec 2023 (before report period)
        opening = self.env["account.move"].create({
            "date": "2023-12-15",
            "journal_id": self.journal.id,
            "move_type": "entry",
            "line_ids": [
                (0, 0, {"account_id": self.account_recv.id, "partner_id": self.partner.id, "debit": 500.0, "credit": 0.0}),
                (0, 0, {"account_id": self.account_rev.id, "debit": 0.0, "credit": 500.0}),
            ],
        })
        opening.action_post()

        # One move in Jan 2024
        move = self.env["account.move"].create({
            "date": "2024-01-15",
            "journal_id": self.journal.id,
            "move_type": "entry",
            "line_ids": [
                (0, 0, {"account_id": self.account_recv.id, "partner_id": self.partner.id, "debit": 100.0, "credit": 0.0}),
                (0, 0, {"account_id": self.account_rev.id, "debit": 0.0, "credit": 100.0}),
            ],
        })
        move.action_post()

        # First page should have opening_balance = 500
        page1 = _get_move_lines_page(
            self.env, self._domain(), self.account_recv.id,
            page_size=1, last_id=0, currency=self.currency,
        )
        self.assertEqual(
            page1.get("opening_balance"), 500.0,
            "opening_balance should be 500.0 but got %s" % page1.get("opening_balance"),
        )
        self.assertEqual(
            page1["balance_before"], 500.0,
            "balance_before should be 500.0 but got %s" % page1["balance_before"],
        )

    def test_last_date_required_with_last_id(self):
        """Bug A: last_date must be provided when last_id > 0."""
        from odoo.addons.general_ledger_enterprise_view.controllers.main import _get_move_lines_page

        move = self.env["account.move"].create({
            "date": "2024-01-15",
            "journal_id": self.journal.id,
            "move_type": "entry",
            "line_ids": [
                (0, 0, {"account_id": self.account_recv.id, "partner_id": self.partner.id, "debit": 100.0, "credit": 0.0}),
                (0, 0, {"account_id": self.account_rev.id, "debit": 0.0, "credit": 100.0}),
            ],
        })
        move.action_post()

        with self.assertRaises(ValueError):
            _get_move_lines_page(
                self.env, self._domain(), self.account_recv.id,
                page_size=1, last_id=999, last_date=None,
                currency=self.currency,
            )

    def test_pl_account_opening_uses_fy_start(self):
        """Bug D: P&L account opening must use fiscal-year start, not all history."""
        from odoo.addons.general_ledger_enterprise_view.controllers.main import _get_move_lines_page

        # Revenue is P&L (include_initial_balance=False)
        # Create a move in 2023 (before FY start of 2024)
        old_move = self.env["account.move"].create({
            "date": "2023-06-15",
            "journal_id": self.journal.id,
            "move_type": "entry",
            "line_ids": [
                (0, 0, {"account_id": self.account_recv.id, "debit": 300.0, "credit": 0.0}),
                (0, 0, {"account_id": self.account_rev.id, "debit": 0.0, "credit": 300.0}),
            ],
        })
        old_move.action_post()

        # Create a move in Jan 2024
        move = self.env["account.move"].create({
            "date": "2024-01-15",
            "journal_id": self.journal.id,
            "move_type": "entry",
            "line_ids": [
                (0, 0, {"account_id": self.account_recv.id, "partner_id": self.partner.id, "debit": 100.0, "credit": 0.0}),
                (0, 0, {"account_id": self.account_rev.id, "debit": 0.0, "credit": 100.0}),
            ],
        })
        move.action_post()

        # For the revenue (P&L) account, opening should be 0 (FY start = Jan 1)
        page = _get_move_lines_page(
            self.env, self._domain(), self.account_rev.id,
            page_size=1, last_id=0, currency=self.currency,
        )
        self.assertEqual(
            page.get("opening_balance"), 0.0,
            "P&L opening should be 0 (FY start), got %s" % page.get("opening_balance"),
        )

        # For the receivable (BS) account, opening should be 300 (all history)
        page_bs = _get_move_lines_page(
            self.env, self._domain(), self.account_recv.id,
            page_size=1, last_id=0, currency=self.currency,
        )
        self.assertEqual(
            page_bs.get("opening_balance"), 300.0,
            "BS opening should be 300 (all history), got %s" % page_bs.get("opening_balance"),
        )