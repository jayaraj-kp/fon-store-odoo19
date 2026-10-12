# License: LGPL-3.0 or later
"""Behaviour-based tests for large-dataset safety of the GL / TB controller.

These tests deliberately do NOT read main.py as text (the old versions did,
which broke on docstrings/comments and depended on the working directory).
They exercise the real functions instead, or inspect the parsed AST, which
ignores comments and docstrings.
"""
import ast
import base64
import inspect
import uuid
from unittest.mock import patch

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.general_ledger_enterprise_view.controllers import main as gl_main


@tagged("post_install", "-at_install")
class TestLargeDatasetPerformance(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ctrl = gl_main.GeneralLedgerEnterpriseController()

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _make_partners(self, count):
        """Create *count* partners sharing a unique name prefix."""
        prefix = "GLCHUNK-%s-" % uuid.uuid4().hex[:8]
        partners = self.env["res.partner"].create(
            [{"name": "%s%03d" % (prefix, i)} for i in range(count)]
        )
        return prefix, partners

    def _chunk_domain(self, prefix):
        return [("name", "=like", prefix + "%")]

    def _attachment_ids(self):
        return set(self.env["ir.attachment"].search([]).ids)

    def _leaked_attachments(self, before_ids):
        """Attachments created since *before_ids*, ignoring asset bundles.

        Rendering QWeb may legitimately cache compiled /web/assets bundles
        as attachments; those are not report/export files.
        """
        new_ids = self._attachment_ids() - before_ids
        new = self.env["ir.attachment"].browse(list(new_ids))
        return new.filtered(lambda a: not (a.url or "").startswith("/web/assets/"))

    @staticmethod
    def _empty_data():
        return {
            "accounts": [],
            "company_name": "Test",
            "date_from": "2024-01-01",
            "date_to": "2024-01-31",
        }

    def _filters(self, report_type="gl"):
        return {
            "date_from": "2024-01-01",
            "date_to": "2024-01-31",
            "company_id": self.env.company.id,
            "report_type": report_type,
        }

    # ------------------------------------------------------------------
    # Cursor pagination (no OFFSET) + streaming
    # ------------------------------------------------------------------
    def test_chunked_cursor_returns_every_record_once_in_id_order(self):
        """5 records / chunk_size=2 -> 3 chunks; nothing skipped or repeated."""
        prefix, partners = self._make_partners(5)
        rows = list(gl_main._chunked_search_read(
            self.env, "res.partner", self._chunk_domain(prefix),
            ["id", "name"], order="id", chunk_size=2,
        ))
        ids = [r["id"] for r in rows]
        self.assertEqual(ids, sorted(partners.ids))
        self.assertEqual(len(ids), len(set(ids)), "duplicate rows returned")

    def test_chunked_cursor_exact_multiple_of_chunk_size(self):
        """4 records / chunk_size=2: the trailing empty chunk must end the loop."""
        prefix, partners = self._make_partners(4)
        rows = list(gl_main._chunked_search_read(
            self.env, "res.partner", self._chunk_domain(prefix),
            ["id"], order="id", chunk_size=2,
        ))
        self.assertEqual([r["id"] for r in rows], sorted(partners.ids))

    def test_chunked_cursor_empty_result(self):
        rows = list(gl_main._chunked_search_read(
            self.env, "res.partner",
            self._chunk_domain("NO-SUCH-PREFIX-%s" % uuid.uuid4().hex),
            ["id"], order="id", chunk_size=2,
        ))
        self.assertEqual(rows, [])

    def test_chunked_search_read_is_lazy_generator(self):
        """Streaming: callers must not need a list() wrapper to avoid loading
        everything at once; the helper has to be a generator."""
        prefix, _partners = self._make_partners(3)
        gen = gl_main._chunked_search_read(
            self.env, "res.partner", self._chunk_domain(prefix),
            ["id"], order="id", chunk_size=2,
        )
        self.assertTrue(inspect.isgenerator(gen))

    # ------------------------------------------------------------------
    # PDF engine: no custom subprocess / shell usage in this module
    # ------------------------------------------------------------------
    def test_module_does_not_use_subprocess_or_shell(self):
        """AST-based (ignores comments/docstrings, independent of cwd)."""
        tree = ast.parse(inspect.getsource(gl_main))
        forbidden_modules = {"subprocess"}
        forbidden_os_calls = {"system", "popen"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(
                        alias.name.split(".")[0], forbidden_modules,
                        "controller must not import %s" % alias.name,
                    )
            elif isinstance(node, ast.ImportFrom):
                self.assertNotIn(
                    (node.module or "").split(".")[0], forbidden_modules,
                    "controller must not import from %s" % node.module,
                )
            elif isinstance(node, ast.Attribute):
                if (isinstance(node.value, ast.Name) and node.value.id == "os"
                        and node.attr in forbidden_os_calls):
                    self.fail("controller must not call os.%s" % node.attr)

    def test_pdf_export_uses_native_engine_and_returns_base64(self):
        """PDF goes through Odoo's own _run_wkhtmltopdf and comes back as
        base64 content (not a URL). wkhtmltopdf itself is mocked, so the test
        also works on servers where the binary is not installed."""
        fake_pdf = b"%PDF-1.4 fake-content"
        report_cls = type(self.env["ir.actions.report"])
        for report_type in ("gl", "tb"):
            with self.subTest(report_type=report_type):
                with patch.object(
                    report_cls, "_run_wkhtmltopdf", return_value=fake_pdf
                ) as mocked:
                    result = self.ctrl._export_pdf(
                        self.env, report_type, self._empty_data(),
                        self._filters(report_type),
                    )
                mocked.assert_called_once()
                self.assertIn("file_content", result)
                self.assertIn("file_name", result)
                self.assertNotIn("url", result)
                self.assertTrue(result["file_name"].endswith(".pdf"))
                self.assertEqual(base64.b64decode(result["file_content"]), fake_pdf)

    # ------------------------------------------------------------------
    # Exports must not leave ir.attachment records behind
    # ------------------------------------------------------------------
    def test_xlsx_export_creates_no_attachment(self):
        before = self._attachment_ids()
        for report_type in ("gl", "tb"):
            with self.subTest(report_type=report_type):
                result = self.ctrl._export_xlsx(
                    self.env, report_type, self._empty_data(),
                    self._filters(report_type),
                )
                self.assertIn("file_content", result)
                self.assertNotIn("url", result)
        self.assertFalse(
            self._leaked_attachments(before),
            "XLSX export must not create ir.attachment records",
        )

    def test_pdf_export_creates_no_attachment(self):
        before = self._attachment_ids()
        report_cls = type(self.env["ir.actions.report"])
        with patch.object(report_cls, "_run_wkhtmltopdf", return_value=b"%PDF-1.4 x"):
            for report_type in ("gl", "tb"):
                with self.subTest(report_type=report_type):
                    self.ctrl._export_pdf(
                        self.env, report_type, self._empty_data(),
                        self._filters(report_type),
                    )
        self.assertFalse(
            self._leaked_attachments(before),
            "PDF export must not create ir.attachment records",
        )

    # ------------------------------------------------------------------
    # Input validation
    # ------------------------------------------------------------------
    def test_grouped_by_validation(self):
        """An invalid grouped_by falls back to 'none' instead of crashing."""
        result = gl_main.compute_enterprise_gl_data(
            self.env,
            date_from="2024-01-01",
            date_to="2024-01-31",
            grouped_by="invalid_option",
        )
        self.assertIn("accounts", result)