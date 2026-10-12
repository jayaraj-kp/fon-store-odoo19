# Copyright 2024 YourCompany
# License: LGPL-3.0 or later

from odoo.tests import tagged

from .common import FSEnterpriseCommon

_REPORT_MODEL = "report.financial_statements_enterprise_view.fs_pdf"


@tagged("post_install", "-at_install")
class TestPdfCompanyHeader(FSEnterpriseCommon):
    """The PDF header (name / logo / VAT) must belong to the company the
    report was computed for, not to the user's active company."""

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.company_a = cls.company_data["company"]
        cls.company_b = cls.company_data_2["company"]
        group_field = (
            "groups_id" if "groups_id" in cls.env["res.users"]._fields else "group_ids"
        )
        group = cls.env.ref("account.group_account_user")
        cls.user_both = cls.env["res.users"].create({
            "name": "FS PDF Both", "login": "fs_pdf_both",
            "company_id": cls.company_a.id,
            "company_ids": [(6, 0, [cls.company_a.id, cls.company_b.id])],
            group_field: [(6, 0, [group.id])],
        })
        cls.user_only_a = cls.env["res.users"].create({
            "name": "FS PDF Only A", "login": "fs_pdf_only_a",
            "company_id": cls.company_a.id,
            "company_ids": [(6, 0, [cls.company_a.id])],
            group_field: [(6, 0, [group.id])],
        })

    def test_requested_company_used_in_template_values(self):
        model = self.env[_REPORT_MODEL].with_user(self.user_both).with_context(
            allowed_company_ids=[self.company_a.id])
        values = model._get_report_values(
            [], data={"company_id": self.company_b.id, "report_type": "bs"})
        self.assertEqual(values["company"], self.company_b)

    def test_default_is_active_company_when_not_supplied(self):
        model = self.env[_REPORT_MODEL].with_user(self.user_both).with_context(
            allowed_company_ids=[self.company_a.id])
        values = model._get_report_values([], data={"report_type": "bs"})
        self.assertEqual(values["company"], self.company_a)

    def test_inaccessible_company_is_ignored(self):
        """data can arrive via the generic /report/pdf route: a user must
        never get another company's name/logo/VAT through it."""
        model = self.env[_REPORT_MODEL].with_user(self.user_only_a)
        values = model._get_report_values(
            [], data={"company_id": self.company_b.id, "report_type": "bs"})
        self.assertEqual(values["company"], self.company_a)

    def test_invalid_company_id_is_ignored(self):
        model = self.env[_REPORT_MODEL].with_user(self.user_both).with_context(
            allowed_company_ids=[self.company_a.id])
        values = model._get_report_values(
            [], data={"company_id": "not-a-number", "report_type": "bs"})
        self.assertEqual(values["company"], self.company_a)