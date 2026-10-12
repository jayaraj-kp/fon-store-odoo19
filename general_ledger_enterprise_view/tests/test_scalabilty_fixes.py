# License: LGPL-3.0 or later
"""Tests for: (1) binary export builders, (2) last_balance cursor,
(3) partner pagination. Put this file in the module's tests/ folder and
import it from tests/__init__.py."""
import base64
import io
import zipfile

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.general_ledger_enterprise_view.controllers import main as gl_main


@tagged("post_install", "-at_install")
class TestScalabilityFixes(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        Account = cls.env["account.account"]
        cls.recv = Account.create({
            "code": "GLPG01", "name": "GL PG Receivable",
            "account_type": "asset_receivable",
            "company_ids": [(6, 0, [cls.company.id])],
        })
        cls.inc = Account.create({
            "code": "GLPG02", "name": "GL PG Income",
            "account_type": "income",
            "company_ids": [(6, 0, [cls.company.id])],
        })
        cls.journal = cls.env["account.journal"].create({
            "name": "GL PG", "code": "GLPG", "type": "general",
            "company_id": cls.company.id,
        })
        cls.partners = cls.env["res.partner"].create(
            [{"name": "GLPG-%s" % c} for c in "ABCDE"])
        # opening move (Dec 2023) + one move per partner in Mar 2024
        cls._move("2023-12-15", cls.partners[0], 500.0)
        for i, partner in enumerate(cls.partners):
            cls._move("2024-03-%02d" % (10 + i), partner, 100.0 + i)

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

    def _domain(self):
        return gl_main._build_gl_base_domain(self.company, "posted") + [
            ("date", ">=", "2024-03-01"), ("date", "<=", "2024-03-31")]

    # ---------------- (2) last_balance cursor ----------------------------
    def test_cursor_balance_equals_server_balance(self):
        kw = dict(account_id=self.recv.id, page_size=2,
                  currency=self.company.currency_id, company=self.company)
        p1 = gl_main._get_move_lines_page(self.env, self._domain(), **kw)
        self.assertEqual(p1["opening_balance"], 500.0)
        cursor = dict(last_id=p1["last_id"], last_date=p1["last_date"])
        old_way = gl_main._get_move_lines_page(self.env, self._domain(), **kw, **cursor)
        new_way = gl_main._get_move_lines_page(
            self.env, self._domain(), **kw, **cursor,
            last_balance=p1["lines"][-1]["balance"])
        self.assertEqual(old_way["lines"], new_way["lines"])
        self.assertEqual(old_way["balance_before"], new_way["balance_before"])
        self.assertEqual(old_way["has_more"], new_way["has_more"])
        self.assertIsNone(new_way["opening_balance"])  # only page 1 needs it

    def test_last_balance_ignored_on_first_page(self):
        kw = dict(account_id=self.recv.id, page_size=1,
                  currency=self.company.currency_id, company=self.company)
        with_it = gl_main._get_move_lines_page(
            self.env, self._domain(), **kw, last_balance=99999.0)
        without = gl_main._get_move_lines_page(self.env, self._domain(), **kw)
        self.assertEqual(with_it["lines"], without["lines"])
        self.assertEqual(with_it["opening_balance"], 500.0)

    def test_invalid_last_balance_rejected(self):
        for bad in ("abc", float("nan"), float("inf")):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    gl_main._get_move_lines_page(
                        self.env, self._domain(), self.recv.id,
                        last_id=1, last_date="2024-03-10", last_balance=bad,
                        currency=self.company.currency_id)

    # ---------------- (3) partner pagination -----------------------------
    def _tb(self, **kw):
        data = gl_main.compute_enterprise_gl_data(
            self.env, date_from="2024-03-01", date_to="2024-03-31",
            company_id=self.company.id, account_ids=[self.recv.id],
            report_type="tb", include_lines=False, **kw)
        return next(a for a in data["accounts"] if a["id"] == self.recv.id)

    def test_partner_pages_cover_unpaged_list_in_same_order(self):
        full = self._tb()
        self.assertFalse(full["partners_has_more"])
        full_ids = [g["id"] for g in full["partner_groups"]]
        self.assertEqual(len(full_ids), 5)

        seen, offset, guard = [], 0, 0
        while True:
            guard += 1
            self.assertLess(guard, 10)
            page = self._tb(partner_limit=2, partner_offset=offset)
            self.assertLessEqual(len(page["partner_groups"]), 2)
            seen += [g["id"] for g in page["partner_groups"]]
            # account totals never depend on the page
            self.assertEqual(page["fin_bal"], full["fin_bal"])
            self.assertEqual(page["init_bal"], full["init_bal"])
            if not page["partners_has_more"]:
                break
            offset = page["partner_offset_next"]
        self.assertEqual(seen, full_ids)

    def test_exact_multiple_has_no_phantom_next_page(self):
        page = self._tb(partner_limit=5)
        self.assertEqual(len(page["partner_groups"]), 5)
        self.assertFalse(page["partners_has_more"])

    def test_partner_limit_ignored_with_lines_and_validated(self):
        data = gl_main.compute_enterprise_gl_data(
            self.env, date_from="2024-03-01", date_to="2024-03-31",
            company_id=self.company.id, account_ids=[self.recv.id],
            report_type="tb", include_lines=True, partner_limit=1)
        acc = next(a for a in data["accounts"] if a["id"] == self.recv.id)
        self.assertEqual(len(acc["partner_groups"]), 5)
        with self.assertRaises(UserError):
            self._tb(partner_limit="abc")

    # ---------------- (1) binary export builders -------------------------
    def test_binary_xlsx_matches_json_flavour(self):
        ctrl = gl_main.GeneralLedgerEnterpriseController()
        data = gl_main.compute_enterprise_gl_data(
            self.env, date_from="2024-03-01", date_to="2024-03-31",
            company_id=self.company.id, account_ids=[self.recv.id])
        filters = {"date_from": "2024-03-01", "date_to": "2024-03-31",
                   "company_id": self.company.id, "report_type": "gl"}
        raw, name = ctrl._build_xlsx(self.env, "gl", data, filters)
        legacy = ctrl._export_xlsx(self.env, "gl", data, filters)
        self.assertEqual(name, legacy["file_name"])

        def sheet(blob):
            return zipfile.ZipFile(io.BytesIO(blob)).read("xl/worksheets/sheet1.xml")
        self.assertEqual(sheet(raw), sheet(base64.b64decode(legacy["file_content"])))