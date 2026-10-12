# License: LGPL-3.0 or later
"""Tests for scalability round 3:
(a) SQL partner paging must give EXACTLY what the ORM/Python path gives;
(b) streaming XLSX must equal the eager XLSX, and big exports become jobs.
Put this file in the module's tests/ folder and import it from
tests/__init__.py."""
import base64
import io
import json
import zipfile
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.general_ledger_enterprise_view.controllers import main as gl_main


@tagged("post_install", "-at_install")
class TestSqlPartnerPaging(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        Account = cls.env["account.account"]
        cls.recv = Account.create({
            "code": "GLSQ01", "name": "GL SQ Receivable",
            "account_type": "asset_receivable",
            "company_ids": [(6, 0, [cls.company.id])],
        })
        cls.inc = Account.create({
            "code": "GLSQ02", "name": "GL SQ Income",
            "account_type": "income",
            "company_ids": [(6, 0, [cls.company.id])],
        })
        cls.journal = cls.env["account.journal"].create({
            "name": "GL SQ", "code": "GLSQ", "type": "general",
            "company_id": cls.company.id,
        })
        # mixed case / accents / punctuation: ordering must match Python's
        names = ["zeta", "Alpha", "alpha-2", "Émile", "bob", "Bob 2", "MIKE", "x"]
        cls.partners = cls.env["res.partner"].create(
            [{"name": "GLSQ %s" % n} for n in names])
        for i, partner in enumerate(cls.partners):
            cls._move("2023-12-15", partner, 100.0 + i)       # opening
        for i, partner in enumerate(cls.partners[:6]):
            cls._move("2024-03-%02d" % (10 + i), partner, 10.0 + i)  # period
        # settled partner: opening and period both net to zero -> hidden
        settled = cls.env["res.partner"].create({"name": "GLSQ settled"})
        cls._move("2023-11-01", settled, 50.0)
        cls._move("2023-11-02", settled, -50.0)
        # entry without partner -> "Unknown Partner" bucket (pid 0)
        cls._move("2024-03-20", cls.env["res.partner"], 7.0)

    @classmethod
    def _move(cls, date, partner, amount):
        debit, credit = (amount, 0.0) if amount >= 0 else (0.0, -amount)
        move = cls.env["account.move"].create({
            "date": date, "journal_id": cls.journal.id, "move_type": "entry",
            "line_ids": [
                (0, 0, {"account_id": cls.recv.id, "partner_id": partner.id or False,
                        "debit": debit, "credit": credit}),
                (0, 0, {"account_id": cls.inc.id, "debit": credit, "credit": debit}),
            ],
        })
        move.action_post()

    def _tb(self, report_type="tb", grouped_by="none", **kw):
        data = gl_main.compute_enterprise_gl_data(
            self.env, date_from="2024-03-01", date_to="2024-03-31",
            company_id=self.company.id, account_ids=[self.recv.id, self.inc.id],
            report_type=report_type, grouped_by=grouped_by,
            include_lines=False, **kw)
        return next(a for a in data["accounts"] if a["id"] == self.recv.id)

    def _pages(self, limit, **kw):
        out, offset, guard = [], 0, 0
        while True:
            guard += 1
            self.assertLess(guard, 30)
            acc = self._tb(partner_limit=limit, partner_offset=offset, **kw)
            self.assertLessEqual(len(acc["partner_groups"]), limit)
            out.append(acc)
            if not acc["partners_has_more"]:
                return out
            offset = acc["partner_offset_next"]

    def test_sql_pages_equal_orm_pages(self):
        for limit in (1, 3, 100):
            for kw in ({}, {"report_type": "gl", "grouped_by": "partners"}):
                with self.subTest(limit=limit, kw=kw):
                    with patch.object(gl_main, "_USE_SQL_PARTNER_PAGING", False):
                        orm = self._pages(limit, **kw)
                    sql = self._pages(limit, **kw)
                    self.assertEqual(
                        [a["partner_groups"] for a in orm],
                        [a["partner_groups"] for a in sql])
                    self.assertEqual(
                        [(a["partners_has_more"], a["partner_offset_next"]) for a in orm],
                        [(a["partners_has_more"], a["partner_offset_next"]) for a in sql])
                    # account totals never depend on the page
                    self.assertEqual(orm[0]["fin_bal"], sql[0]["fin_bal"])
                    self.assertEqual(orm[0]["init_bal"], sql[0]["init_bal"])

    def test_settled_partner_is_hidden_and_unknown_bucket_present(self):
        groups = self._tb(partner_limit=100)["partner_groups"]
        names = [g["name"] for g in groups]
        self.assertNotIn("GLSQ settled", names)
        self.assertIn("Unknown Partner", names)

    def test_sql_failure_falls_back_to_orm(self):
        with patch.object(gl_main, "_aml_domain_sql", side_effect=RuntimeError("sql-boom")):
            with self.assertLogs(gl_main._logger, level="WARNING"):
                acc = self._tb(partner_limit=3)
        with patch.object(gl_main, "_USE_SQL_PARTNER_PAGING", False):
            expected = self._tb(partner_limit=3)
        self.assertEqual(acc["partner_groups"], expected["partner_groups"])

    def test_non_trade_account_has_no_partner_groups_in_tb(self):
        data = gl_main.compute_enterprise_gl_data(
            self.env, date_from="2024-03-01", date_to="2024-03-31",
            company_id=self.company.id, account_ids=[self.inc.id],
            report_type="tb", include_lines=False, partner_limit=5)
        acc = next(a for a in data["accounts"] if a["id"] == self.inc.id)
        self.assertFalse(acc["has_partners"])


@tagged("post_install", "-at_install")
class TestStreamingXlsxAndJobs(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        Account = cls.env["account.account"]
        cls.recv = Account.create({
            "code": "GLST01", "name": "GL ST Receivable",
            "account_type": "asset_receivable",
            "company_ids": [(6, 0, [cls.company.id])],
        })
        cls.inc = Account.create({
            "code": "GLST02", "name": "GL ST Income",
            "account_type": "income",
            "company_ids": [(6, 0, [cls.company.id])],
        })
        cls.journal = cls.env["account.journal"].create({
            "name": "GL ST", "code": "GLST", "type": "general",
            "company_id": cls.company.id,
        })
        cls.partners = cls.env["res.partner"].create(
            [{"name": "GLST-%s" % c} for c in "ABC"])
        cls._move("2023-12-15", cls.partners[0], 500.0)
        for i in range(7):  # more than the stream page size used below
            cls._move("2024-03-%02d" % (5 + i), cls.partners[i % 3], 100.0 + i)

    @classmethod
    def _move(cls, date, partner, amount):
        move = cls.env["account.move"].create({
            "date": date, "journal_id": cls.journal.id, "move_type": "entry",
            "line_ids": [
                (0, 0, {"account_id": cls.recv.id, "partner_id": partner.id,
                        "debit": amount, "credit": 0.0}),
                (0, 0, {"account_id": cls.inc.id, "debit": 0.0, "credit": amount}),
            ],
        })
        move.action_post()

    def _filters(self, report_type, **extra):
        f = {"date_from": "2024-03-01", "date_to": "2024-03-31",
             "company_id": self.company.id, "report_type": report_type,
             "account_ids": [self.recv.id, self.inc.id]}
        f.update(extra)
        return f

    @staticmethod
    def _sheet(blob):
        return zipfile.ZipFile(io.BytesIO(blob)).read("xl/worksheets/sheet1.xml")

    def _eager(self, filters):
        ctrl = gl_main.GeneralLedgerEnterpriseController()
        report_type, data = ctrl._compute_export_data(self.env, "xlsx", filters)
        return ctrl._build_xlsx(self.env, report_type, data, filters)[0]

    def _streamed(self, filters):
        ctrl = gl_main.GeneralLedgerEnterpriseController()
        report_type, data = gl_main._compute_streaming_xlsx_data(self.env, filters)
        return ctrl._build_xlsx(self.env, report_type, data, filters)[0]

    def test_streaming_gl_equals_eager(self):
        # tiny pages force several keyset round-trips
        with patch.object(gl_main, "_EXPORT_STREAM_PAGE", 2):
            f = self._filters("gl")
            self.assertEqual(self._sheet(self._streamed(f)), self._sheet(self._eager(f)))

    def test_streaming_tb_unfold_equals_eager(self):
        with patch.object(gl_main, "_EXPORT_STREAM_PAGE", 2):
            f = self._filters("tb", unfold_all=True)
            self.assertEqual(self._sheet(self._streamed(f)), self._sheet(self._eager(f)))

    def test_streaming_tb_without_unfold_equals_eager(self):
        f = self._filters("tb")
        self.assertEqual(self._sheet(self._streamed(f)), self._sheet(self._eager(f)))

    def test_stream_generator_is_lazy_and_ordered(self):
        domain = gl_main._build_gl_base_domain(self.company, "posted") + [
            ("date", ">=", "2024-03-01"), ("date", "<=", "2024-03-31")]
        with patch.object(gl_main, "_EXPORT_STREAM_PAGE", 2):
            gen = gl_main._stream_line_dicts(
                self.env, domain, self.recv.id, 500.0, self.company.currency_id)
            self.assertTrue(hasattr(gen, "__next__"))
            lines = list(gen)
        self.assertEqual(len(lines), 7)
        self.assertEqual([l["date"] for l in lines], sorted(l["date"] for l in lines))
        self.assertEqual(lines[0]["balance"], 600.0)  # 500 opening + 100

    def test_big_export_requires_background_job(self):
        with patch.object(gl_main, "_MAX_EXPORT_ROWS", 3):
            with self.assertRaises(gl_main._BackgroundExportRequired):
                gl_main._compute_streaming_xlsx_data(self.env, self._filters("gl"))
        with patch.object(gl_main, "_MAX_BACKGROUND_EXPORT_ROWS", 3):
            with self.assertRaises(UserError):
                gl_main._compute_streaming_xlsx_data(self.env, self._filters("gl"))

    def test_background_job_builds_same_file(self):
        filters = self._filters("gl")
        Job = self.env["gl.export.job"]
        job = Job._queue_export(filters, "xlsx", 999)
        self.assertEqual(job.state, "queued")
        # same filters twice -> same job (double click protection)
        self.assertEqual(Job._queue_export(filters, "xlsx", 999), job)
        with patch.object(type(job), "_check_user_can_export", lambda self, user: None):
            job._process()
        self.assertEqual(job.state, "done", job.error_message)
        self.assertEqual(
            self._sheet(base64.b64decode(job.file)), self._sheet(self._eager(filters)))
        self.assertEqual(json.loads(job.filters_json)["report_type"], "gl")
        action = job.action_download()
        self.assertIn("/web/content/gl.export.job/%s/file/" % job.id, action["url"])

    def test_failed_job_is_recorded_not_raised(self):
        job = self.env["gl.export.job"]._queue_export(self._filters("gl"), "xlsx", 10)
        with patch.object(type(job), "_build_file", side_effect=RuntimeError("job-boom")):
            job._process()
        self.assertEqual(job.state, "failed")
        self.assertIn("job-boom", job.error_message)

    def test_job_requires_accounting_group(self):
        job = self.env["gl.export.job"]._queue_export(self._filters("gl"), "xlsx", 10)
        with patch.object(type(self.env["res.users"]), "has_group", lambda self, g: False):
            job._process()
        self.assertEqual(job.state, "failed")