# Copyright 2024 YourCompany
# License: LGPL-3.0 or later

from odoo.tests import tagged

from .common import FSEnterpriseCommon


@tagged("post_install", "-at_install")
class TestAnalyticAccountIdsCompute(FSEnterpriseCommon):

    def test_analytic_account_ids_populated_from_distribution(self):
        analytic_1 = self.env["account.analytic.account"].create(
            {"name": "Analytic 1", "company_id": self.company_data["company"].id}
        )
        analytic_2 = self.env["account.analytic.account"].create(
            {"name": "Analytic 2", "company_id": self.company_data["company"].id}
        )
        move = self.env["account.move"].create({
            "move_type": "entry",
            "date": "2024-06-01",
            "journal_id": self.journal_misc.id,
            "line_ids": [
                (0, 0, {
                    "account_id": self.account_asset.id, "debit": 100.0,
                    "credit": 0.0, "name": "/",
                    "analytic_distribution": {
                        str(analytic_1.id): 60.0,
                        str(analytic_2.id): 40.0,
                    },
                }),
                (0, 0, {
                    "account_id": self.account_payable.id,
                    "debit": 0.0, "credit": 100.0, "name": "/",
                }),
            ],
        })
        line = move.line_ids.filtered(lambda l: l.account_id == self.account_asset)
        self.assertEqual(set(line.analytic_account_ids.ids), {analytic_1.id, analytic_2.id})

    def test_no_distribution_means_no_analytic_accounts(self):
        move = self.env["account.move"].create({
            "move_type": "entry",
            "date": "2024-06-01",
            "journal_id": self.journal_misc.id,
            "line_ids": [
                (0, 0, {"account_id": self.account_asset.id,
                        "debit": 50.0, "credit": 0.0, "name": "/"}),
                (0, 0, {"account_id": self.account_payable.id,
                        "debit": 0.0, "credit": 50.0, "name": "/"}),
            ],
        })
        line = move.line_ids.filtered(lambda l: l.account_id == self.account_asset)
        self.assertFalse(line.analytic_account_ids)

    def test_deleted_analytic_account_is_skipped_gracefully(self):
        """If an analytic account referenced by an old distribution key
        was since deleted, the compute must skip it rather than crash —
        this is exactly what the existing_account_ids/.exists() guard in
        account_move_line.py is for."""
        analytic = self.env["account.analytic.account"].create(
            {"name": "Temp Analytic", "company_id": self.company_data["company"].id}
        )
        analytic_id = analytic.id
        move = self.env["account.move"].create({
            "move_type": "entry",
            "date": "2024-06-01",
            "journal_id": self.journal_misc.id,
            "line_ids": [
                (0, 0, {
                    "account_id": self.account_asset.id, "debit": 100.0,
                    "credit": 0.0, "name": "/",
                    "analytic_distribution": {str(analytic_id): 100.0},
                }),
                (0, 0, {
                    "account_id": self.account_payable.id,
                    "debit": 0.0, "credit": 100.0, "name": "/",
                }),
            ],
        })
        analytic.unlink()
        line = move.line_ids.filtered(lambda l: l.account_id == self.account_asset)
        # force a recompute now that the analytic account no longer exists
        line._compute_analytic_account_ids()
        self.assertFalse(line.analytic_account_ids)


@tagged("post_install", "-at_install")
class TestAnalyticDistributionSearchParity(FSEnterpriseCommon):
    """SAFETY NET before the stored ``analytic_account_ids`` helper is ever
    removed: searching ``analytic_distribution`` directly (core mixin) must
    return exactly the same journal lines as the helper, including
    partial-percent and multi-plan ("a,b") keys, and ``= False`` must find
    only lines with no distribution at all (drill-down of 'Unassigned')."""

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        company = cls.company_data["company"]
        plan_a = cls.env["account.analytic.plan"].create({"name": "Parity Plan A"})
        plan_b = cls.env["account.analytic.plan"].create({"name": "Parity Plan B"})
        Analytic = cls.env["account.analytic.account"]
        cls.a1 = Analytic.create({"name": "PA1", "plan_id": plan_a.id, "company_id": company.id})
        cls.a2 = Analytic.create({"name": "PA2", "plan_id": plan_a.id, "company_id": company.id})
        cls.b1 = Analytic.create({"name": "PB1", "plan_id": plan_b.id, "company_id": company.id})

    def _line(self, distribution):
        move = self._post_entry("2024-06-01", [
            (self.account_asset, 10.0, 0.0), (self.account_payable, 0.0, 10.0)])
        line = move.line_ids.filtered(lambda l: l.account_id == self.account_asset)
        if distribution:
            line.analytic_distribution = distribution
        return line

    def test_in_search_matches_m2m_helper(self):
        l_single = self._line({str(self.a1.id): 100})
        l_split = self._line({str(self.a1.id): 60, str(self.a2.id): 40})
        l_partial = self._line({str(self.a1.id): 30})
        l_composite = self._line({f"{self.a1.id},{self.b1.id}": 100})
        l_other = self._line({str(self.a2.id): 100})
        l_none = self._line(None)
        mine = (l_single | l_split | l_partial | l_composite | l_other | l_none)

        AML = self.env["account.move.line"]
        base = [("id", "in", mine.ids)]
        via_dist = AML.search(base + [("analytic_distribution", "in", [self.a1.id])])
        via_m2m = AML.search(base + [("analytic_account_ids", "in", [self.a1.id])])
        expected = l_single | l_split | l_partial | l_composite
        self.assertEqual(set(via_m2m.ids), set(expected.ids), "helper baseline changed")
        self.assertEqual(
            set(via_dist.ids), set(via_m2m.ids),
            "analytic_distribution search differs from the stored helper "
            "(check multi-plan 'a,b' keys / partial %) - do NOT drop the "
            "helper field until this passes.")

    def test_equals_false_finds_only_undistributed_lines(self):
        l_none = self._line(None)
        l_tagged = self._line({str(self.a1.id): 100})
        AML = self.env["account.move.line"]
        found = AML.search([
            ("id", "in", (l_none | l_tagged).ids),
            ("analytic_distribution", "=", False)])
        self.assertEqual(found, l_none)