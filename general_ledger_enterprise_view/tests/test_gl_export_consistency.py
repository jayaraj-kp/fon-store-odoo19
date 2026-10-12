# License: LGPL-3.0 or later
"""GL screen, PDF and XLSX must show the same account / grand-total balance:
opening + period movement (fin_bal.ending_balance)."""
import base64
import datetime
import io
import re
import zipfile
from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.general_ledger_enterprise_view.controllers import main as gl_main


@tagged("post_install", "-at_install")
class TestGLExportConsistency(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ctrl = gl_main.GeneralLedgerEnterpriseController()
        # opening 100, period debit 50 / credit 20 -> ending 130 (movement 30)
        cls.data = {
            "company_name": "Test", "date_from": "2024-01-01", "date_to": "2024-01-31",
            "accounts": [{
                "id": 1, "code": "1000", "name": "Recv",
                "init_bal": {"debit": 100.0, "credit": 0.0, "balance": 100.0},
                "fin_bal": {"debit": 50.0, "credit": 20.0, "balance": 30.0,
                            "ending_balance": 130.0},
                "move_lines": [{
                    "date": "2024-01-10", "move_name": "MISC/1", "partner": "P",
                    "debit": 50.0, "credit": 20.0, "balance": 130.0,
                }],
            }],
        }
        cls.filters = {"date_from": "2024-01-01", "date_to": "2024-01-31",
                       "company_id": cls.env.company.id, "report_type": "gl"}

    def test_helpers(self):
        acc = self.data["accounts"][0]
        self.assertEqual(gl_main._gl_account_init_balance(acc), 100.0)
        self.assertEqual(gl_main._gl_account_ending_balance(acc), 130.0)
        legacy = {"init_bal": {"balance": 10.0}, "fin_bal": {"debit": 5.0, "credit": 2.0}}
        self.assertEqual(gl_main._gl_account_ending_balance(legacy), 13.0)

    def test_xlsx_gl_total_is_ending_balance(self):
        result = self.ctrl._export_xlsx(self.env, "gl", self.data, self.filters)
        zf = zipfile.ZipFile(io.BytesIO(base64.b64decode(result["file_content"])))
        sheet = zf.read("xl/worksheets/sheet1.xml").decode()
        values = re.findall(r"<v>([-\d.]+)</v>", sheet)
        # account row (130), opening row (100), line running balance (130).
        # The grand total carries no Balance (GL has no Unallocated Earnings
        # row), and it is never 30 (debit - credit).
        self.assertEqual(values.count("130"), 2, values)
        self.assertIn("100", values)
        self.assertNotIn("30", values)

    def test_pdf_gl_shows_opening_and_ending(self):
        captured = {}

        def fake_run(report, bodies, **kw):
            captured["html"] = bodies[0]
            return b"%PDF-1.4 x"

        report_cls = type(self.env["ir.actions.report"])
        with patch.object(report_cls, "_run_wkhtmltopdf", fake_run):
            self.ctrl._export_pdf(self.env, "gl", self.data, self.filters)
        html = str(captured["html"])
        self.assertIn("Initial Balance", html)
        self.assertIn("100.00", html)
        self.assertIn("130.00", html)
        self.assertNotIn(">30.00", html.replace(" ", ""))


@tagged("post_install", "-at_install")
class TestGLInitFiscalYear(TransactionCase):
    """/gl_enterprise/init must expose the company fiscal-year start so the
    UI does not assume Jan-Dec."""

    def test_init_returns_fiscal_year_start(self):
        ctrl = gl_main.GeneralLedgerEnterpriseController()
        fake_request = type("R", (), {"env": self.env})()
        with patch.object(gl_main, "request", fake_request), \
                patch.object(gl_main, "_check_account_group", lambda: None):
            res = ctrl.get_init_data(company_id=self.env.company.id)
        fy_from = datetime.date.fromisoformat(res["date_from"])
        self.assertEqual(res["fiscalyear_start_month"], fy_from.month)
        self.assertEqual(res["fiscalyear_start_day"], fy_from.day)

    def test_init_returns_company_accounts(self):
        """The accounts dropdown must not be empty (account.account has only
        company_ids in Odoo 19; a company_id leaf used to fail silently)."""
        company = self.env.company
        account = self.env["account.account"].create({
            "code": "GLINIT01", "name": "GL Init Test",
            "account_type": "asset_current",
            "company_ids": [(6, 0, [company.id])],
        })
        ctrl = gl_main.GeneralLedgerEnterpriseController()
        fake_request = type("R", (), {"env": self.env})()
        with patch.object(gl_main, "request", fake_request), \
                patch.object(gl_main, "_check_account_group", lambda: None):
            res = ctrl.get_init_data(company_id=company.id)
        self.assertTrue(res["accounts"])
        self.assertIn(account.id, [a["id"] for a in res["accounts"]])


@tagged("post_install", "-at_install")
class TestGLErrorHandling(TransactionCase):
    """Unexpected failures surface as UserError carrying the real cause;
    Odoo's own user-facing errors keep their type."""

    def _compute(self):
        return gl_main.compute_enterprise_gl_data(
            self.env, date_from="2024-01-01", date_to="2024-01-31")

    def test_unexpected_error_becomes_usererror_with_cause(self):
        aml_cls = type(self.env["account.move.line"])
        with patch.object(aml_cls, "_read_group", side_effect=RuntimeError("boom-123")):
            with self.assertRaises(UserError) as ctx:
                self._compute()
        message = str(ctx.exception)
        self.assertIn("boom-123", message)       # no bare/unformatted "%s"
        self.assertNotIn("%s", message)

    def test_access_error_is_not_rewrapped(self):
        aml_cls = type(self.env["account.move.line"])
        with patch.object(aml_cls, "_read_group", side_effect=AccessError("denied-xyz")):
            with self.assertRaises(AccessError):
                self._compute()


@tagged("post_install", "-at_install")
class TestGLInputValidation(TransactionCase):
    """account_ids / partner_ids / journal_ids / last_date validation and
    the fiscal-year helper no longer failing silently."""

    def test_sanitize_id_list_valid(self):
        f = gl_main._sanitize_id_list
        self.assertEqual(f(None, "x"), [])
        self.assertEqual(f([], "x"), [])
        # falsy skipped, numeric strings/floats accepted, dupes dropped
        self.assertEqual(f([1, "2", 3.0, 0, None, 2], "x"), [1, 2, 3])
        # the UI's "match nothing" sentinel must keep working
        self.assertEqual(f([-1], "x"), [-1])

    def test_sanitize_id_list_invalid(self):
        f = gl_main._sanitize_id_list
        for bad in ("abc", 5, [1, "a"], [True], [1.5], [10 ** 12], [{"a": 1}]):
            with self.subTest(bad=bad):
                with self.assertRaises(UserError):
                    f(bad, "account_ids")
        with self.assertRaises(UserError):
            f(list(range(1, gl_main._MAX_FILTER_IDS + 2)), "account_ids")

    def test_domain_builder_validates(self):
        company = self.env.company
        dom = gl_main._build_gl_base_domain(
            company, "posted", account_ids=["5", 6], partner_ids=[7], journal_ids=[8])
        self.assertIn(("account_id", "in", [5, 6]), dom)
        self.assertIn(("partner_id", "in", [7]), dom)
        self.assertIn(("journal_id", "in", [8]), dom)
        with self.assertRaises(UserError):
            gl_main._build_gl_base_domain(company, "posted", account_ids=["abc"])

    def test_compute_rejects_bad_filters(self):
        with self.assertRaises(UserError):
            gl_main.compute_enterprise_gl_data(
                self.env, date_from="2024-01-01", date_to="2024-01-31",
                partner_ids="not-a-list")
        with self.assertRaises(UserError):
            gl_main.compute_enterprise_gl_data(
                self.env, date_from="2024-01-01", date_to="2024-01-31",
                account_ids=[1, "x"])

    def test_get_lines_invalid_last_date(self):
        ctrl = gl_main.GeneralLedgerEnterpriseController()
        fake_request = type("R", (), {"env": self.env})()
        with patch.object(gl_main, "request", fake_request), \
                patch.object(gl_main, "_check_account_group", lambda: None):
            with self.assertRaises(UserError):
                ctrl.get_lines(
                    account_id=1, date_from="2024-01-01", date_to="2024-01-31",
                    last_id=5, last_date="not-a-date")

    def test_fiscal_year_start_failure_is_logged(self):
        company = self.env.company
        company_cls = type(company)
        with patch.object(company_cls, "compute_fiscalyear_dates",
                          side_effect=RuntimeError("fy-boom"), create=True):
            with self.assertLogs(gl_main._logger, level="WARNING") as logs:
                result = gl_main._get_fiscal_year_start(company, datetime.date(2024, 5, 10))
        self.assertTrue(any("fy-boom" in line for line in logs.output))
        self.assertIsInstance(result, datetime.date)  # still falls back safely