# Copyright 2024 YourCompany
# License: LGPL-3.0 or later
"""Regression tests for the SQL-based analytic (warehouse) columns.

They exercise _get_account_balances_batch() with REAL tagged journal lines.
(The old performance test only passed analytic ids that had no lines at
all, so the batch path was never executed.)
"""
from odoo.tests import tagged

from .common import FSEnterpriseCommon


@tagged("post_install", "-at_install")
class TestAnalyticBatchSQL(FSEnterpriseCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.company = cls.company_data["company"]
        Plan = cls.env["account.analytic.plan"]
        cls.plan_a = Plan.create({"name": "FS Plan A"})
        cls.plan_b = Plan.create({"name": "FS Plan B"})
        Analytic = cls.env["account.analytic.account"]
        cls.a1 = Analytic.create({"name": "Dammam", "plan_id": cls.plan_a.id,
                                  "company_id": cls.company.id})
        cls.a2 = Analytic.create({"name": "Riyadh", "plan_id": cls.plan_a.id,
                                  "company_id": cls.company.id})
        cls.b1 = Analytic.create({"name": "Project X", "plan_id": cls.plan_b.id,
                                  "company_id": cls.company.id})

    def _tag(self, move, account, distribution):
        line = move.line_ids.filtered(lambda l: l.account_id == account)
        line.analytic_distribution = distribution

    def _batch(self, ids, date_to="2024-12-31"):
        return self.engine._get_account_balances_batch(
            self.company, date_to=date_to, analytic_account_ids=ids)

    def test_single_tag_and_split_percentages(self):
        m1 = self._post_entry("2024-06-01", [
            (self.account_asset, 100.0, 0.0), (self.account_payable, 0.0, 100.0)])
        self._tag(m1, self.account_asset, {str(self.a1.id): 100})
        m2 = self._post_entry("2024-06-02", [
            (self.account_asset, 100.0, 0.0), (self.account_payable, 0.0, 100.0)])
        self._tag(m2, self.account_asset, {str(self.a1.id): 60, str(self.a2.id): 40})
        res = self._batch([self.a1.id, self.a2.id])
        self.assertAlmostEqual(res[self.a1.id][self.account_asset.id], 160.0)
        self.assertAlmostEqual(res[self.a2.id][self.account_asset.id], 40.0)

    def test_multi_plan_key_gets_full_percentage_each(self):
        """{"a,b": 100} = BOTH accounts get 100% (Odoo core semantics)."""
        m = self._post_entry("2024-06-01", [
            (self.account_asset, 200.0, 0.0), (self.account_payable, 0.0, 200.0)])
        self._tag(m, self.account_asset, {f"{self.a1.id},{self.b1.id}": 100})
        res = self._batch([self.a1.id, self.b1.id])
        self.assertAlmostEqual(res[self.a1.id][self.account_asset.id], 200.0)
        self.assertAlmostEqual(res[self.b1.id][self.account_asset.id], 200.0)

    def test_untagged_lines_and_unselected_analytics_ignored(self):
        self._post_entry("2024-06-01", [
            (self.account_asset, 50.0, 0.0), (self.account_payable, 0.0, 50.0)])
        res = self._batch([self.a1.id])
        self.assertEqual(res[self.a1.id], {})

    def test_draft_and_date_filters_respected(self):
        m = self._post_entry("2025-03-01", [
            (self.account_asset, 70.0, 0.0), (self.account_payable, 0.0, 70.0)])
        self._tag(m, self.account_asset, {str(self.a1.id): 100})
        self.assertEqual(self._batch([self.a1.id], "2024-12-31")[self.a1.id], {})
        self.assertAlmostEqual(
            self._batch([self.a1.id], "2025-12-31")[self.a1.id][self.account_asset.id], 70.0)

    def test_zero_total_account_stays_visible_when_forced(self):
        """+25 in one warehouse, -25 in another -> total 0. Without the
        context flag the row vanished and section != sum(children)."""
        acc = self.env["account.account"].create({
            "name": "FS Transit Liab", "code": "FSTL01",
            "account_type": "liability_current",
            "company_ids": [(6, 0, [self.company.id])],
        })
        m1 = self._post_entry("2024-06-01", [
            (self.account_asset, 25.0, 0.0), (acc, 0.0, 25.0)])
        self._tag(m1, acc, {str(self.a1.id): 100})
        m2 = self._post_entry("2024-06-02", [
            (acc, 25.0, 0.0), (self.account_asset, 0.0, 25.0)])
        self._tag(m2, acc, {str(self.a2.id): 100})

        leaf_id = f"ocl_acc_{acc.id}"
        plain = self.engine.get_balance_sheet(
            date_to="2024-12-31", company_id=self.company.id)
        self.assertIsNone(self.find_line(plain["lines"], leaf_id))
        forced = self.engine.with_context(
            fs_force_account_ids=(acc.id,)).get_balance_sheet(
            date_to="2024-12-31", company_id=self.company.id)
        self.assertIsNotNone(self.find_line(forced["lines"], leaf_id))

    def test_query_count_independent_of_line_volume(self):
        """3 SQL aggregations for BS no matter how many lines exist."""
        for i in range(30):
            m = self._post_entry("2024-06-01", [
                (self.account_asset, 1.0, 0.0), (self.account_payable, 0.0, 1.0)])
            self._tag(m, self.account_asset, {str(self.a1.id): 100})
        cr = self.env.cr
        original, counter = cr.execute, {"n": 0}

        def counting(*a, **k):
            counter["n"] += 1
            return original(*a, **k)
        cr.execute = counting
        try:
            self._batch([self.a1.id, self.a2.id])
        finally:
            cr.execute = original
        self.assertLessEqual(counter["n"], 3)


@tagged("post_install", "-at_install")
class TestUnassignedColumn(FSEnterpriseCommon):
    """The optional "Unassigned" column: whatever is not covered by an
    analytic distribution, so that
        sum(analytic columns) + Unassigned == Total
    holds even when some lines are untagged or only partly distributed."""

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.company = cls.company_data["company"]
        plan = cls.env["account.analytic.plan"].create({"name": "FS Unassigned Plan"})
        plan2 = cls.env["account.analytic.plan"].create({"name": "FS Unassigned Plan 2"})
        Analytic = cls.env["account.analytic.account"]
        cls.a1 = Analytic.create({"name": "Dammam", "plan_id": plan.id,
                                  "company_id": cls.company.id})
        cls.a2 = Analytic.create({"name": "Riyadh", "plan_id": plan.id,
                                  "company_id": cls.company.id})
        cls.b1 = Analytic.create({"name": "Project X", "plan_id": plan2.id,
                                  "company_id": cls.company.id})

    def _asset_entry(self, date, amount, distribution=None):
        move = self._post_entry(date, [
            (self.account_asset, amount, 0.0), (self.account_payable, 0.0, amount)])
        if distribution:
            line = move.line_ids.filtered(lambda l: l.account_id == self.account_asset)
            line.analytic_distribution = distribution
        return move

    def _report(self, ids, include_unassigned, report_type="bs"):
        return self.engine.get_analytic_report(
            report_type, "2024-01-01", "2024-12-31", self.company.id,
            analytic_account_ids=ids, include_unassigned=include_unassigned)

    # -- SQL level -------------------------------------------------------
    def test_unassigned_share_per_line(self):
        """untagged=100%, fully tagged=0%, 60% tagged=40%, multi-plan key
        at 100% = 0% (one slice shared by two plans, not two slices)."""
        self._asset_entry("2024-06-01", 50.0)                                # 50
        self._asset_entry("2024-06-02", 100.0, {str(self.a1.id): 100})       # 0
        self._asset_entry("2024-06-03", 100.0, {str(self.a1.id): 60})        # 40
        self._asset_entry("2024-06-04", 200.0,
                          {f"{self.a1.id},{self.b1.id}": 100})               # 0
        res = self.engine._get_unassigned_balances(
            self.company, date_to="2024-12-31")
        self.assertAlmostEqual(res[self.account_asset.id], 90.0)

    def test_unassigned_respects_draft_and_date_filters(self):
        self._asset_entry("2025-03-01", 70.0)   # after date_to
        res = self.engine._get_unassigned_balances(
            self.company, date_to="2024-12-31")
        self.assertNotIn(self.account_asset.id, res)

    # -- report level ----------------------------------------------------
    def test_columns_sum_equals_total_balance_sheet(self):
        self._asset_entry("2024-06-01", 100.0, {str(self.a1.id): 100})
        self._asset_entry("2024-06-02", 100.0,
                          {str(self.a1.id): 60, str(self.a2.id): 40})
        self._asset_entry("2024-06-03", 70.0)                                # untagged
        self._asset_entry("2024-06-04", 100.0, {str(self.a2.id): 50})        # half tagged
        result = self._report([self.a1.id, self.a2.id], True)
        ab = self.find_line(result["lines"], "assets")["analytic_balances"]
        self.assertAlmostEqual(ab[self.a1.id], 160.0)
        self.assertAlmostEqual(ab[self.a2.id], 90.0)
        self.assertAlmostEqual(ab["unassigned"], 120.0)   # 70 + 50
        self.assertAlmostEqual(ab["total"], 370.0)
        self.assertAlmostEqual(
            ab[self.a1.id] + ab[self.a2.id] + ab["unassigned"], ab["total"])

    def test_columns_sum_equals_total_profit_and_loss(self):
        self._post_entry("2024-03-10", [
            (self.account_receivable, 1000.0, 0.0),
            (self.account_revenue, 0.0, 1000.0)])
        line = self.env["account.move.line"].search([
            ("account_id", "=", self.account_revenue.id),
            ("credit", "=", 1000.0)], limit=1)
        line.analytic_distribution = {str(self.a1.id): 25}
        result = self._report([self.a1.id], True, report_type="pl")
        ab = self.find_line(result["lines"], "revenue")["analytic_balances"]
        self.assertAlmostEqual(ab[self.a1.id], 250.0)
        self.assertAlmostEqual(ab["unassigned"], 750.0)
        self.assertAlmostEqual(ab[self.a1.id] + ab["unassigned"], ab["total"])

    # -- column visibility (the filter option) ----------------------------
    def test_unassigned_column_hidden_when_not_selected(self):
        self._asset_entry("2024-06-01", 70.0)
        result = self._report([self.a1.id], False)
        self.assertEqual(
            [c["id"] for c in result["analytic_columns"]], [self.a1.id, "total"])
        ab = self.find_line(result["lines"], "assets")["analytic_balances"]
        self.assertNotIn("unassigned", ab)

    def test_unassigned_column_shown_when_selected(self):
        result = self._report([self.a1.id], True)
        self.assertEqual(
            [c["id"] for c in result["analytic_columns"]],
            [self.a1.id, "unassigned", "total"])

    def test_unassigned_only_filter(self):
        """No analytic account picked, only 'Unassigned' ticked."""
        self._asset_entry("2024-06-01", 70.0)
        result = self._report([], True)
        self.assertEqual(
            [c["id"] for c in result["analytic_columns"]], ["unassigned", "total"])
        ab = self.find_line(result["lines"], "assets")["analytic_balances"]
        self.assertAlmostEqual(ab["unassigned"], 70.0)
        self.assertAlmostEqual(ab["unassigned"], ab["total"])

    def test_unassigned_row_visible_when_total_nets_to_zero(self):
        """+25 unassigned and -25 tagged on the same account: the account
        total is 0 but the Unassigned column must still show its row."""
        acc = self.env["account.account"].create({
            "name": "FS Unassigned Transit", "code": "FSUN01",
            "account_type": "liability_current",
            "company_ids": [(6, 0, [self.company.id])],
        })
        m1 = self._post_entry("2024-06-01", [
            (self.account_asset, 25.0, 0.0), (acc, 0.0, 25.0)])           # untagged
        m2 = self._post_entry("2024-06-02", [
            (acc, 25.0, 0.0), (self.account_asset, 0.0, 25.0)])
        m2.line_ids.filtered(lambda l: l.account_id == acc).analytic_distribution = {
            str(self.a1.id): 100}
        result = self._report([self.a1.id], True)
        leaf = self.find_line(result["lines"], f"ocl_acc_{acc.id}")
        self.assertIsNotNone(leaf)
        self.assertAlmostEqual(leaf["analytic_balances"]["unassigned"], 25.0)
        self.assertAlmostEqual(leaf["analytic_balances"][self.a1.id], -25.0)
        self.assertAlmostEqual(leaf["analytic_balances"]["total"], 0.0)