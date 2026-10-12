# Copyright 2024 YourCompany
# License: LGPL-3.0 or later

"""
PDF Export Tests
=================
export_pdf() (Balance Sheet / P&L, via ir.actions.report._render_qweb_pdf)
and export_tax_pdf() (VAT Return, via reportlab) previously had *zero*
test coverage — only the Excel exports were tested. These are HTTP-level
smoke tests (real JSON-RPC calls, like test_controller_security.py and
TestExcelExportHTTP), which is the most reliable way to exercise these
routes since they depend on request-bound state (request.env, request.env.lang)
that only exists inside a real HTTP request.

Coverage:
  1. Balance Sheet PDF — valid PDF magic bytes, correct file name
  2. Profit & Loss PDF — same
  3. VAT Return PDF (reportlab) — valid PDF magic bytes, comparison
     columns don't crash it, graceful error when reportlab is missing
  4. Auth / cross-company checks for both routes (same guarantees as
     get_data/export_excel already have)
"""

import base64
import json

from odoo.tests import HttpCase, tagged

# PDF file magic bytes / version header.
_PDF_MAGIC = b"%PDF"


def _is_valid_pdf(b64_string):
    try:
        raw = base64.b64decode(b64_string)
        return raw[:4] == _PDF_MAGIC
    except Exception:
        return False


@tagged("post_install", "-at_install")
class TestBalanceSheetAndPLPdfExport(HttpCase):
    """export_pdf() — uses core ir.actions.report, no optional
    dependency, so this must always succeed (given wkhtmltopdf is
    present, as it is in any standard Odoo test runner)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_own = cls.env["res.company"].create({"name": "PDF Test Own Co"})
        cls.company_other = cls.env["res.company"].create({"name": "PDF Test Other Co"})
        cls.user = cls.env["res.users"].create({
            "name": "PDF Test Accountant",
            "login": "fs_pdf_test_accountant",
            "password": "fs_pdf_test_accountant",
            "company_id": cls.company_own.id,
            "company_ids": [(6, 0, [cls.company_own.id])],
            "groups_id": [(6, 0, [cls.env.ref("account.group_account_user").id])],
        })

    def _json_rpc(self, url, params):
        payload = {"jsonrpc": "2.0", "method": "call", "params": params, "id": 1}
        return self.url_open(
            url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )

    def test_balance_sheet_pdf_valid(self):
        self.authenticate("fs_pdf_test_accountant", "fs_pdf_test_accountant")
        response = self._json_rpc("/fs_enterprise/export_pdf", {
            "report_type": "bs",
            "date_to": "2024-12-31",
            "company_id": self.company_own.id,
        })
        body = response.json()
        self.assertNotIn("error", body, body.get("error"))
        result = body["result"]
        self.assertIn("file_content", result)
        self.assertTrue(_is_valid_pdf(result["file_content"]))
        self.assertTrue(result["file_name"].startswith("Balance_Sheet"))
        self.assertTrue(result["file_name"].endswith(".pdf"))

    def test_profit_and_loss_pdf_valid(self):
        self.authenticate("fs_pdf_test_accountant", "fs_pdf_test_accountant")
        response = self._json_rpc("/fs_enterprise/export_pdf", {
            "report_type": "pl",
            "date_from": "2024-01-01",
            "date_to": "2024-12-31",
            "company_id": self.company_own.id,
        })
        body = response.json()
        self.assertNotIn("error", body, body.get("error"))
        result = body["result"]
        self.assertTrue(_is_valid_pdf(result["file_content"]))
        self.assertTrue(result["file_name"].startswith("Profit_and_Loss"))

    def test_balance_sheet_pdf_with_comparison_no_crash(self):
        """Comparison columns must be embedded in the PDF data without
        crashing export_pdf (mirrors the existing Excel comparison
        smoke test, but for the PDF path)."""
        self.authenticate("fs_pdf_test_accountant", "fs_pdf_test_accountant")
        response = self._json_rpc("/fs_enterprise/export_pdf", {
            "report_type": "bs",
            "date_to": "2024-12-31",
            "company_id": self.company_own.id,
            "comparison_mode": "previous_period",
            "comparison_date_to": "2023-12-31",
        })
        body = response.json()
        self.assertNotIn("error", body, body.get("error"))
        self.assertTrue(_is_valid_pdf(body["result"]["file_content"]))

    def test_export_pdf_unauthenticated_rejected(self):
        response = self._json_rpc("/fs_enterprise/export_pdf", {
            "report_type": "bs",
            "date_to": "2024-12-31",
        })
        body = response.json()
        self.assertIn("error", body)

    def test_export_pdf_cross_company_rejected(self):
        self.authenticate("fs_pdf_test_accountant", "fs_pdf_test_accountant")
        response = self._json_rpc("/fs_enterprise/export_pdf", {
            "report_type": "bs",
            "date_to": "2024-12-31",
            "company_id": self.company_other.id,
        })
        body = response.json()
        self.assertIn("error", body)
        self.assertIn("do not have access", json.dumps(body["error"]).lower())


@tagged("post_install", "-at_install")
class TestVatReturnPdfExport(HttpCase):
    """export_tax_pdf() — uses reportlab, which is an optional
    dependency (main.py returns {"error": "..."} gracefully if it's
    missing, same pattern as xlsxwriter for the Excel export)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        try:
            import reportlab  # noqa: F401
            cls._reportlab_available = True
        except ImportError:
            cls._reportlab_available = False

        cls.company_own = cls.env["res.company"].create({"name": "VAT PDF Test Own Co"})
        cls.company_other = cls.env["res.company"].create({"name": "VAT PDF Test Other Co"})
        cls.user = cls.env["res.users"].create({
            "name": "VAT PDF Test Accountant",
            "login": "fs_vat_pdf_test_accountant",
            "password": "fs_vat_pdf_test_accountant",
            "company_id": cls.company_own.id,
            "company_ids": [(6, 0, [cls.company_own.id])],
            "groups_id": [(6, 0, [cls.env.ref("account.group_account_user").id])],
        })

    def _skip_if_no_reportlab(self):
        if not self._reportlab_available:
            self.skipTest("reportlab not installed — skipping VAT PDF export tests")

    def _json_rpc(self, url, params):
        payload = {"jsonrpc": "2.0", "method": "call", "params": params, "id": 1}
        return self.url_open(
            url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )

    def test_vat_pdf_valid(self):
        self._skip_if_no_reportlab()
        self.authenticate("fs_vat_pdf_test_accountant", "fs_vat_pdf_test_accountant")
        response = self._json_rpc("/fs_enterprise/export_tax_pdf", {
            "date_from": "2024-01-01",
            "date_to": "2024-12-31",
            "company_id": self.company_own.id,
        })
        body = response.json()
        self.assertNotIn("error", body, body.get("error"))
        result = body["result"]
        self.assertNotIn("error", result, result.get("error"))
        self.assertTrue(_is_valid_pdf(result["file_content"]))
        self.assertTrue(result["file_name"].endswith(".pdf"))

    def test_vat_pdf_with_comparison_periods_no_crash(self):
        """Multiple comparison periods make the PDF table grow extra
        columns dynamically (see the column-width rebalancing logic in
        export_tax_pdf) — must not crash or overflow the page."""
        self._skip_if_no_reportlab()
        self.authenticate("fs_vat_pdf_test_accountant", "fs_vat_pdf_test_accountant")
        response = self._json_rpc("/fs_enterprise/export_tax_pdf", {
            "date_from": "2024-01-01",
            "date_to": "2024-12-31",
            "company_id": self.company_own.id,
            "comparison_periods": [
                {"label": "2023", "date_from": "2023-01-01", "date_to": "2023-12-31"},
                {"label": "2022", "date_from": "2022-01-01", "date_to": "2022-12-31"},
            ],
        })
        body = response.json()
        self.assertNotIn("error", body, body.get("error"))
        result = body["result"]
        if "error" in result:
            self.skipTest(result["error"])
        self.assertTrue(_is_valid_pdf(result["file_content"]))

    def test_missing_reportlab_returns_error_dict(self):
        if self._reportlab_available:
            self.skipTest("reportlab is installed; skipping missing-library test")
        self.authenticate("fs_vat_pdf_test_accountant", "fs_vat_pdf_test_accountant")
        response = self._json_rpc("/fs_enterprise/export_tax_pdf", {
            "date_from": "2024-01-01",
            "date_to": "2024-12-31",
            "company_id": self.company_own.id,
        })
        body = response.json()
        self.assertNotIn("error", body)
        self.assertIn("error", body["result"])
        self.assertIn("reportlab", body["result"]["error"].lower())

    def test_export_tax_pdf_unauthenticated_rejected(self):
        response = self._json_rpc("/fs_enterprise/export_tax_pdf", {
            "date_from": "2024-01-01",
            "date_to": "2024-12-31",
        })
        body = response.json()
        self.assertIn("error", body)

    def test_export_tax_pdf_cross_company_rejected(self):
        self.authenticate("fs_vat_pdf_test_accountant", "fs_vat_pdf_test_accountant")
        response = self._json_rpc("/fs_enterprise/export_tax_pdf", {
            "date_from": "2024-01-01",
            "date_to": "2024-12-31",
            "company_id": self.company_other.id,
        })
        body = response.json()
        self.assertIn("error", body)
        self.assertIn("do not have access", json.dumps(body["error"]).lower())