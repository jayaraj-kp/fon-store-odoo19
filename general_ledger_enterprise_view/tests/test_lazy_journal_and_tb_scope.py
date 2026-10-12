# License: LGPL-3.0 or later
"""Tests for (1) journal sub-groups in lazy mode (include_lines=False) and
(2) the Trial Balance partner aggregates being limited to receivable/payable."""
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.general_ledger_enterprise_view.controllers import main as gl_main


@tagged("post_install", "-at_install")
class TestLazyJournalAndTbScope(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.company
        Account = cls.env["account.account"]
        cls.acc_recv = Account.create({
            "code": "GLJR01", "name": "GL JR Receivable",
            "account_type": "asset_receivable",
            "company_ids": [(6, 0, [company.id])],
        })
        cls.acc_inc = Account.create({
            "code": "GLJR02", "name": "GL JR Income",
            "account_type": "income",
            "company_ids": [(6, 0, [company.id])],
        })
        Journal = cls.env["account.journal"]
        cls.j_a = Journal.create({"name": "GL JR A", "code": "GJRA",
                                  "type": "general", "company_id": company.id})
        cls.j_b = Journal.create({"name": "GL JR B", "code": "GJRB",
                                  "type": "general", "company_id": company.id})
        cls.partner = cls.env["res.partner"].create({"name": "GL JR Partner"})
        for journal, amount in ((cls.j_a, 100.0), (cls.j_a, 30.0), (cls.j_b, 50.0)):
            move = cls.env["account.move"].create({
                "date": "2024-03-10",
                "journal_id": journal.id,
                "move_type": "entry",
                "line_ids": [
                    (0, 0, {"account_id": cls.acc_recv.id, "partner_id": cls.partner.id,
                            "debit": amount, "credit": 0.0}),
                    (0, 0, {"account_id": cls.acc_inc.id, "debit": 0.0, "credit": amount}),
                ],
            })
            move.action_post()

    def _compute(self, **kw):
        return gl_main.compute_enterprise_gl_data(
            self.env, date_from="2024-03-01", date_to="2024-03-31",
            account_ids=[self.acc_recv.id, self.acc_inc.id], **kw)

    @staticmethod
    def _by_code(data, code):
        return next(a for a in data["accounts"] if a["code"] == code)

    def test_lazy_journal_groups_match_eager(self):
        eager = self._by_code(self._compute(grouped_by="journals", include_lines=True), "GLJR01")
        lazy = self._by_code(self._compute(grouped_by="journals", include_lines=False), "GLJR01")

        def summary(acc):
            return {g["journal_id"]: (g["fin_bal"]["debit"], g["fin_bal"]["credit"])
                    for g in acc["journal_groups"]}

        self.assertTrue(lazy["has_journals"])
        self.assertEqual(summary(lazy), summary(eager))
        self.assertEqual(summary(lazy)[self.j_a.id], (130.0, 0.0))
        self.assertEqual(summary(lazy)[self.j_b.id], (50.0, 0.0))
        # lazy mode never embeds lines (they are loaded via /get_lines)
        self.assertTrue(all(not g["move_lines"] for g in lazy["journal_groups"]))

    def test_no_journal_groups_unless_requested(self):
        lazy = self._by_code(self._compute(grouped_by="none", include_lines=False), "GLJR01")
        self.assertFalse(lazy["has_journals"])

    def test_tb_partner_groups_only_for_trade_accounts(self):
        tb = self._compute(report_type="tb", include_lines=False)
        recv = self._by_code(tb, "GLJR01")
        inc = self._by_code(tb, "GLJR02")
        self.assertTrue(recv["has_partners"])
        self.assertEqual(len(recv["partner_groups"]), 1)
        self.assertEqual(recv["partner_groups"][0]["fin_bal"]["debit"], 180.0)
        self.assertFalse(inc["has_partners"])

    def test_gl_explicit_partner_grouping_not_restricted(self):
        """grouped_by=partners must still work for non-trade accounts."""
        gl = self._compute(grouped_by="partners", include_lines=False)
        inc = self._by_code(gl, "GLJR02")
        self.assertTrue(inc["has_partners"])