# Copyright 2024 YourCompany
# License: LGPL-3.0 or later

from odoo.tests import tagged

from .common import FSEnterpriseCommon, _pick


@tagged("post_install", "-at_install")
class TestReportForNonActiveCompany(FSEnterpriseCommon):
    """User has companies A and B, but A is the ACTIVE one. The report for
    B must still show B's real numbers (not a blank report)."""

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.company_a = cls.company_data["company"]
        cls.company_b = cls.company_data_2["company"]
        group_field = (
            "groups_id" if "groups_id" in cls.env["res.users"]._fields else "group_ids"
        )
        cls.user_ab = cls.env["res.users"].create({
            "name": "FS Multi Co User",
            "login": "fs_multi_co_user",
            "company_id": cls.company_a.id,
            "company_ids": [(6, 0, [cls.company_a.id, cls.company_b.id])],
            group_field: [(6, 0, [cls.env.ref("account.group_account_user").id])],
        })

    def _post_in_company_b(self, amount):
        asset = _pick(self.company_data_2, "default_account_assets", "default_account_asset")
        payable = _pick(self.company_data_2, "default_account_payable")
        journal = _pick(self.company_data_2, "default_journal_misc")
        move = self.env["account.move"].with_company(self.company_b).create({
            "move_type": "entry",
            "date": "2024-06-15",
            "journal_id": journal.id,
            "line_ids": [
                (0, 0, {"account_id": asset.id, "debit": amount, "credit": 0.0, "name": "b"}),
                (0, 0, {"account_id": payable.id, "debit": 0.0, "credit": amount, "name": "b"}),
            ],
        })
        move.action_post()

    def _engine_as_user_with_a_active(self):
        return self.env["financial.report.engine"].with_user(self.user_ab).with_context(
            allowed_company_ids=[self.company_a.id])

    def test_balance_sheet_of_non_active_company_not_blank(self):
        self._post_in_company_b(750.0)
        result = self._engine_as_user_with_a_active().get_balance_sheet(
            date_to="2024-12-31", company_id=self.company_b.id)
        assets = self.find_line(result["lines"], "assets")
        self.assertIsNotNone(assets, "Report for non-active company came out blank")
        self.assertAlmostEqual(assets["balance"], 750.0)

    def test_profit_and_loss_of_non_active_company(self):
        rev = _pick(self.company_data_2, "default_account_revenue", "default_account_income")
        recv = _pick(self.company_data_2, "default_account_receivable")
        journal = _pick(self.company_data_2, "default_journal_misc")
        self.env["account.move"].with_company(self.company_b).create({
            "move_type": "entry", "date": "2024-03-10", "journal_id": journal.id,
            "line_ids": [
                (0, 0, {"account_id": recv.id, "debit": 400.0, "credit": 0.0, "name": "b"}),
                (0, 0, {"account_id": rev.id, "debit": 0.0, "credit": 400.0, "name": "b"}),
            ],
        }).action_post()
        result = self._engine_as_user_with_a_active().get_profit_and_loss(
            date_from="2024-01-01", date_to="2024-12-31",
            company_id=self.company_b.id)
        self.assertAlmostEqual(self.find_line(result["lines"], "net_profit")["balance"], 400.0)

    def test_company_a_report_unchanged(self):
        """Company A (the active one) must be unaffected by the fix."""
        self._post_entry("2024-06-15", [
            (self.account_asset, 100.0, 0.0), (self.account_payable, 0.0, 100.0)])
        result = self._engine_as_user_with_a_active().get_balance_sheet(
            date_to="2024-12-31", company_id=self.company_a.id)
        self.assertAlmostEqual(self.find_line(result["lines"], "assets")["balance"], 100.0)