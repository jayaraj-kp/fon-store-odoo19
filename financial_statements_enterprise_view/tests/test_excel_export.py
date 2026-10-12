# Copyright 2024 YourCompany
# License: LGPL-3.0 or later

"""
Excel Export Smoke Tests
=========================
ഈ test file controller-ലെ export_excel(), export_tax_excel() routes-ന്റെ
correctness verify ചെയ്യുന്നു. "Smoke test" — engine crash ആകുന്നോ,
valid base64 xlsx return ആകുന്നോ, file name correct ആണോ എന്ന് check ചെയ്യുന്നു.

Coverage:
  1. Balance Sheet Excel — basic smoke
  2. P&L Excel — basic smoke
  3. VAT Return Excel — basic smoke
  4. Debit/Credit columns Excel
  5. Comparison columns Excel
  6. Excel output is valid base64-encoded XLSX (magic bytes check)
  7. File name format correct
  8. Empty data — no crash

Note: xlsxwriter install ഇല്ലെങ്കിൽ tests gracefully skip ചെയ്യും.
"""

import base64
import json

from odoo.tests import HttpCase, tagged

from .common import FSEnterpriseCommon


# XLSX file magic bytes: PK zip header (all xlsx files are zip archives)
_XLSX_MAGIC = b"PK\x03\x04"


def _is_valid_xlsx(b64_string):
    """Return True if the base64 string decodes to a valid XLSX (zip) file."""
    try:
        raw = base64.b64decode(b64_string)
        return raw[:4] == _XLSX_MAGIC
    except Exception:
        return False


@tagged("post_install", "-at_install")
class TestExcelExportSmoke(FSEnterpriseCommon):
    """Direct Python-level calls to the controller's internal helpers.

    HttpCase overhead ഇല്ലാതെ controller method directly call ചെയ്ത്
    output verify ചെയ്യുന്നു. xlsxwriter missing ആണെങ്കിൽ
    {"error": "xlsxwriter is not installed..."} return ആകും —
    അത് detect ചെയ്ത് test skip ചെയ്യുന്നു.
    """

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # xlsxwriter available ആണോ check ചെയ്യുന്നു
        try:
            import xlsxwriter  # noqa: F401
            cls._xlsxwriter_available = True
        except ImportError:
            cls._xlsxwriter_available = False

        # Controller instance (routes test ചെയ്യേണ്ടതില്ല, method test ചെയ്യുന്നു)
        from odoo.addons.financial_statements_enterprise_view.controllers.main import (
            FinancialStatementsEnterpriseController,
        )
        cls.controller = FinancialStatementsEnterpriseController()

        # Seed a posted entry so reports have non-zero data
        cls._seed_entry()

    @classmethod
    def _seed_entry(cls):
        """Post one balanced journal entry so Excel sheets have real rows."""
        move = cls.env["account.move"].create({
            "move_type": "entry",
            "date": "2024-06-15",
            "journal_id": cls.journal_misc.id,
            "line_ids": [
                (0, 0, {
                    "account_id": cls.account_asset.id,
                    "debit": 1500.0, "credit": 0.0, "name": "seed",
                }),
                (0, 0, {
                    "account_id": cls.account_payable.id,
                    "debit": 0.0, "credit": 1500.0, "name": "seed",
                }),
            ],
        })
        move.action_post()

    def _skip_if_no_xlsxwriter(self):
        if not self._xlsxwriter_available:
            self.skipTest("xlsxwriter not installed — skipping Excel export tests")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _export_bs(self, **kwargs):
        return self.controller.export_excel(
            report_type="bs",
            date_to="2024-12-31",
            company_id=self.company_data["company"].id,
            **kwargs,
        )

    def _export_pl(self, **kwargs):
        return self.controller.export_excel(
            report_type="pl",
            date_from="2024-01-01",
            date_to="2024-12-31",
            company_id=self.company_data["company"].id,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Balance Sheet Excel
    # ------------------------------------------------------------------

    def test_balance_sheet_excel_returns_file_content(self):
        """export_excel(bs) must return a dict with file_content and file_name."""
        self._skip_if_no_xlsxwriter()
        result = self._export_bs()
        self.assertNotIn(
            "error", result,
            f"Unexpected error in BS excel export: {result.get('error')}",
        )
        self.assertIn("file_content", result)
        self.assertIn("file_name", result)

    def test_balance_sheet_excel_is_valid_xlsx(self):
        """file_content must decode to a valid XLSX (zip) file."""
        self._skip_if_no_xlsxwriter()
        result = self._export_bs()
        self.assertTrue(
            _is_valid_xlsx(result["file_content"]),
            "Balance Sheet Excel file_content is not a valid XLSX (bad magic bytes)",
        )

    def test_balance_sheet_excel_file_name_format(self):
        """file_name must contain 'Balance_Sheet' and the date_to."""
        self._skip_if_no_xlsxwriter()
        result = self._export_bs()
        self.assertIn("Balance_Sheet", result["file_name"])
        self.assertIn("2024-12-31", result["file_name"])
        self.assertTrue(result["file_name"].endswith(".xlsx"))

    # ------------------------------------------------------------------
    # Profit & Loss Excel
    # ------------------------------------------------------------------

    def test_profit_and_loss_excel_returns_file_content(self):
        """export_excel(pl) must return file_content without error."""
        self._skip_if_no_xlsxwriter()
        result = self._export_pl()
        self.assertNotIn("error", result)
        self.assertIn("file_content", result)

    def test_profit_and_loss_excel_is_valid_xlsx(self):
        self._skip_if_no_xlsxwriter()
        result = self._export_pl()
        self.assertTrue(
            _is_valid_xlsx(result["file_content"]),
            "P&L Excel file_content is not a valid XLSX",
        )

    def test_profit_and_loss_excel_file_name_format(self):
        self._skip_if_no_xlsxwriter()
        result = self._export_pl()
        self.assertIn("Profit_and_Loss", result["file_name"])
        self.assertTrue(result["file_name"].endswith(".xlsx"))

    # ------------------------------------------------------------------
    # Debit / Credit columns
    # ------------------------------------------------------------------

    def test_balance_sheet_with_debit_credit_no_crash(self):
        """with_debit_credit=True must produce a valid xlsx, not crash."""
        self._skip_if_no_xlsxwriter()
        result = self._export_bs(with_debit_credit=True)
        self.assertNotIn("error", result)
        self.assertTrue(_is_valid_xlsx(result["file_content"]))

    def test_pl_with_debit_credit_no_crash(self):
        self._skip_if_no_xlsxwriter()
        result = self._export_pl(with_debit_credit=True)
        self.assertNotIn("error", result)
        self.assertTrue(_is_valid_xlsx(result["file_content"]))

    # ------------------------------------------------------------------
    # Comparison columns
    # ------------------------------------------------------------------

    def test_balance_sheet_with_comparison_no_crash(self):
        """Passing a single comparison date must produce a valid xlsx."""
        self._skip_if_no_xlsxwriter()
        result = self._export_bs(
            comparison_mode="previous_period",
            comparison_date_to="2023-12-31",
        )
        self.assertNotIn("error", result)
        self.assertTrue(_is_valid_xlsx(result["file_content"]))

    def test_balance_sheet_multi_period_comparison_no_crash(self):
        """Multiple comparison periods must be handled without crash."""
        self._skip_if_no_xlsxwriter()
        periods = [
            {"label": "2023", "date_to": "2023-12-31"},
            {"label": "2022", "date_to": "2022-12-31"},
        ]
        result = self._export_bs(
            comparison_mode="previous_period",
            comparison_periods=periods,
        )
        self.assertNotIn("error", result)
        self.assertTrue(_is_valid_xlsx(result["file_content"]))

    # ------------------------------------------------------------------
    # Empty data (no journal entries)
    # ------------------------------------------------------------------

    def test_balance_sheet_empty_period_no_crash(self):
        """A future period with no entries must return a valid (empty) xlsx."""
        self._skip_if_no_xlsxwriter()
        result = self.controller.export_excel(
            report_type="bs",
            date_to="2099-12-31",
            company_id=self.company_data["company"].id,
        )
        # Either a valid xlsx or an xlsxwriter-missing error — no Python crash
        self.assertIn("file_content", result)
        self.assertTrue(_is_valid_xlsx(result["file_content"]))

    # ------------------------------------------------------------------
    # xlsxwriter missing → graceful error dict
    # ------------------------------------------------------------------

    def test_missing_xlsxwriter_returns_error_dict(self):
        """If xlsxwriter is not installed, export_excel must return
        {'error': '...'} instead of raising an ImportError."""
        if self._xlsxwriter_available:
            self.skipTest("xlsxwriter is installed; skipping missing-library test")

        result = self._export_bs()
        self.assertIn("error", result)
        self.assertIn("xlsxwriter", result["error"].lower())


@tagged("post_install", "-at_install")
class TestVATExcelExportSmoke(FSEnterpriseCommon):
    """Smoke tests for VAT Return Excel export (export_tax_excel route)."""

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        try:
            import xlsxwriter  # noqa: F401
            cls._xlsxwriter_available = True
        except ImportError:
            cls._xlsxwriter_available = False

        from odoo.addons.financial_statements_enterprise_view.controllers.main import (
            FinancialStatementsEnterpriseController,
        )
        cls.controller = FinancialStatementsEnterpriseController()

    def _skip_if_no_xlsxwriter(self):
        if not self._xlsxwriter_available:
            self.skipTest("xlsxwriter not installed")

    def _export_vat(self, **kwargs):
        # FIX: the controller method/route is export_tax_xlsx (see
        # main.py and financial_reports_view_esm.js) — this test used to
        # call a non-existent export_tax_excel(), which raised
        # AttributeError and made every test in this class fail outright
        # instead of exercising the VAT Excel export at all.
        return self.controller.export_tax_xlsx(
            date_from="2024-01-01",
            date_to="2024-12-31",
            company_id=self.company_data["company"].id,
            **kwargs,
        )

    def test_vat_excel_returns_file_content(self):
        self._skip_if_no_xlsxwriter()
        result = self._export_vat()
        self.assertNotIn(
            "error", result,
            f"Unexpected error in VAT excel export: {result.get('error')}",
        )
        self.assertIn("file_content", result)
        self.assertIn("file_name", result)

    def test_vat_excel_is_valid_xlsx(self):
        self._skip_if_no_xlsxwriter()
        result = self._export_vat()
        self.assertTrue(
            _is_valid_xlsx(result["file_content"]),
            "VAT Excel file_content is not a valid XLSX",
        )

    def test_vat_excel_file_name_contains_date(self):
        self._skip_if_no_xlsxwriter()
        result = self._export_vat()
        self.assertIn("2024-12-31", result["file_name"])
        self.assertTrue(result["file_name"].endswith(".xlsx"))

    def test_vat_excel_empty_period_no_crash(self):
        """No tax transactions → still returns a valid (empty) xlsx."""
        self._skip_if_no_xlsxwriter()
        result = self._export_vat(date_from="2099-01-01", date_to="2099-12-31")
        self.assertIn("file_content", result)
        self.assertTrue(_is_valid_xlsx(result["file_content"]))

    def test_vat_excel_with_comparison_no_crash(self):
        """Comparison periods must not crash the VAT Excel export."""
        self._skip_if_no_xlsxwriter()
        result = self._export_vat(
            comparison_periods=[
                {"label": "Prev Q", "date_from": "2023-10-01", "date_to": "2023-12-31"},
            ],
        )
        self.assertNotIn("error", result)
        self.assertTrue(_is_valid_xlsx(result["file_content"]))


@tagged("post_install", "-at_install")
class TestExcelExportHTTP(HttpCase):
    """HTTP-level smoke tests: real JSON-RPC calls to export_excel endpoint.

    Controller route + auth middleware + real HTTP stack validate ആകുന്നു.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        try:
            import xlsxwriter  # noqa: F401
            cls._xlsxwriter_available = True
        except ImportError:
            cls._xlsxwriter_available = False

        cls.company = cls.env["res.company"].create({"name": "Excel Test Co"})
        cls.user = cls.env["res.users"].create({
            "name": "Excel Test User",
            "login": "excel_test_user",
            "password": "excel_test_user",
            "company_id": cls.company.id,
            "company_ids": [(6, 0, [cls.company.id])],
            "groups_id": [(6, 0, [cls.env.ref("account.group_account_user").id])],
        })

    def _json_rpc(self, url, params):
        payload = {"jsonrpc": "2.0", "method": "call", "params": params, "id": 1}
        return self.url_open(
            url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )

    def _skip_if_no_xlsxwriter(self):
        if not self._xlsxwriter_available:
            self.skipTest("xlsxwriter not installed")

    def test_export_excel_bs_authenticated(self):
        """Authenticated user must get a valid response (file_content or
        xlsxwriter-missing error) — not a 401 or Python traceback."""
        self.authenticate("excel_test_user", "excel_test_user")
        response = self._json_rpc("/fs_enterprise/export_excel", {
            "report_type": "bs",
            "date_to": "2024-12-31",
            "company_id": self.company.id,
        })
        body = response.json()
        # No JSON-RPC protocol error (auth / routing failure)
        self.assertNotIn(
            "error", body,
            f"Unexpected JSON-RPC error: {body.get('error')}",
        )
        result = body.get("result", {})
        # Either file_content (xlsxwriter present) or error key (xlsxwriter missing)
        self.assertTrue(
            "file_content" in result or "error" in result,
            f"Unexpected result shape: {result}",
        )

    def test_export_excel_unauthenticated_rejected(self):
        """Anonymous callers must be rejected by auth='user'."""
        response = self._json_rpc("/fs_enterprise/export_excel", {
            "report_type": "bs",
            "date_to": "2024-12-31",
        })
        body = response.json()
        self.assertIn("error", body)

    def test_export_excel_cross_company_rejected(self):
        """Cross-company export attempt must be rejected with AccessError."""
        other_company = self.env["res.company"].create({"name": "Other Excel Co"})
        self.authenticate("excel_test_user", "excel_test_user")
        response = self._json_rpc("/fs_enterprise/export_excel", {
            "report_type": "bs",
            "date_to": "2024-12-31",
            "company_id": other_company.id,
        })
        body = response.json()
        self.assertIn("error", body)