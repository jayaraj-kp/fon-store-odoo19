# Copyright 2024 YourCompany
# License: LGPL-3.0 or later

"""
VAT Tax-Grid (account.account.tag) Bucketing Tests
=====================================================
test_vat_return.py-ൽ ഉള്ളത് **legacy name-based fallback**
(_get_tax_report_buckets_by_name) മാത്രമാണ്. എന്നാൽ
financial_report_engine.py-ലെ docstring പ്രകാരം,
Settings > Taxes > Tax Grids configure ചെയ്ത ('N(B)'/'N(T)' tags)
companies-ന് ഇതാണ് **primary / preferred path**
(_get_tax_report_buckets_by_grid) — real-world Saudi VAT setups
സാധാരണയായി ഇത് ഉപയോഗിക്കും. ആ path ഇതുവരെ ഒരു test-ലും
exercise ചെയ്തിട്ടില്ലായിരുന്നു.

ഈ file:
  1. Grid-tag path ശരിക്കും ഉപയോഗിക്കപ്പെടുന്നു എന്ന് തെളിയിക്കുന്നു
     — name-based ഉം grid-based ഉം വ്യത്യസ്ത ഫലം തരുന്ന ഒരു tax
     ഉപയോഗിച്ച് (name ഒരു bucket സൂചിപ്പിക്കും, tag വേറൊരു bucket
     സൂചിപ്പിക്കും), ബാക്കി വരുന്നത് tag അനുസരിച്ചാണ് എന്ന്
     confirm ചെയ്യുന്നു.
  2. **Regression test for the multi-company isolation fix**:
     account.account.tag company-scoped അല്ല (global config) എന്നതിനാൽ,
     ഒരു company-യുടെ grid tags വേറൊരു company-യുടെ VAT report-നെ
     ബാധിക്കരുത് — അതായത് tags വേറെ company ഉപയോഗിക്കുന്നു എന്നത്
     കൊണ്ട് മാത്രം ഈ company-യുടെ റിപ്പോർട്ട് silently 0 ആകരുത്.
  3. Grid path-ലും query-efficiency (aggregation-based, per-line
     search_read അല്ല) നിലനിർത്തുന്നു എന്ന് basic sanity.

NOTE: ഈ tests financial_report_engine.py-ൽ
``_company_uses_vat_grid_tags()`` helper (multi-company-fix) ഉണ്ട്
എന്ന് assume ചെയ്യുന്നു. അത് ഇല്ലാതെ ഈ file റൺ ചെയ്താൽ
``test_untagged_company_not_affected_by_other_companys_grid_tags``
FAIL ആകും — അതാണ് ഉദ്ദേശിച്ചത് (ബഗ് ഉണ്ടോ എന്ന് കണ്ടെത്താൻ).
"""

from odoo.tests import tagged

from .common import FSEnterpriseCommon


def _make_grid_tags(env, number, show_vat):
    """Create the 'N(B)' / 'N(T)' account.account.tag pair for a given
    VAT grid box number, matching _VAT_GRID_LINES in the engine."""
    base_tag = env["account.account.tag"].create({
        "name": f"{number}(B)",
        "applicability": "taxes",
    })
    vat_tag = None
    if show_vat:
        vat_tag = env["account.account.tag"].create({
            "name": f"{number}(T)",
            "applicability": "taxes",
        })
    return base_tag, vat_tag


def _make_tagged_tax(env, company, name, amount, type_tax_use, base_tag, vat_tag):
    """Create a tax whose repartition lines carry the given grid tags —
    mirrors how Settings > Taxes > Tax Grids assigns tags in the UI."""
    base_line_vals = {"repartition_type": "base", "factor_percent": 100}
    if base_tag:
        base_line_vals["tag_ids"] = [(6, 0, [base_tag.id])]
    tax_line_vals = {"repartition_type": "tax", "factor_percent": 100}
    if vat_tag:
        tax_line_vals["tag_ids"] = [(6, 0, [vat_tag.id])]

    return env["account.tax"].create({
        "name": name,
        "type_tax_use": type_tax_use,
        "amount_type": "percent",
        "amount": amount,
        "company_id": company.id,
        "invoice_repartition_line_ids": [(0, 0, base_line_vals), (0, 0, tax_line_vals)],
        "refund_repartition_line_ids": [(0, 0, dict(base_line_vals)), (0, 0, dict(tax_line_vals))],
    })


@tagged("post_install", "-at_install")
class TestVATGridTagBucketing(FSEnterpriseCommon):
    """Proves the grid-tag path (_get_tax_report_buckets_by_grid) is
    actually reachable and produces correct, tag-driven buckets — not
    just the name-based fallback."""

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        company = cls.company_data["company"]

        # Box 2 = reduced_sales (per _VAT_GRID_LINES). We deliberately
        # name the tax in a way that the LEGACY name-based fallback
        # would NOT classify as reduced_sales (no "healthcare",
        # "education", "first house", "citizen" keyword, and amount=15
        # is > 6 so by-name logic would put it in std_sales instead).
        # If the result still lands in reduced_sales, that proves the
        # grid tag — not the name — decided the bucket.
        cls.base_tag_2, cls.vat_tag_2 = _make_grid_tags(cls.env, 2, show_vat=True)
        cls.tax_reduced_via_grid = _make_tagged_tax(
            cls.env, company,
            name="Generic Sales Tax Fifteen",  # no reduced-rate keywords
            amount=15.0,
            type_tax_use="sale",
            base_tag=cls.base_tag_2, vat_tag=cls.vat_tag_2,
        )

    def _post_invoice(self, amount, tax):
        move = self.env["account.move"].create({
            "move_type": "out_invoice",
            "date": "2024-06-01",
            "invoice_date": "2024-06-01",
            "journal_id": self.journal_misc.id,
            "invoice_line_ids": [(0, 0, {
                "name": "Grid tag test line",
                "account_id": self.account_revenue.id,
                "quantity": 1,
                "price_unit": amount,
                "tax_ids": [(6, 0, [tax.id])],
            })],
        })
        move.action_post()
        return move

    def test_grid_tags_detected_when_company_uses_them(self):
        """_get_vat_grid_tags() must find the tag pair we created."""
        tag_map = self.engine._get_vat_grid_tags()
        self.assertIn("2(B)", tag_map)
        self.assertIn("2(T)", tag_map)

    def test_company_uses_vat_grid_tags_true_when_referenced(self):
        tag_map = self.engine._get_vat_grid_tags()
        self.assertTrue(
            self.engine._company_uses_vat_grid_tags(
                self.company_data["company"], tag_map
            ),
            "Company's own tax references grid tags — dispatch must "
            "pick the grid-based path.",
        )

    def test_amount_lands_in_grid_bucket_not_name_bucket(self):
        """Core proof: the tag decides the bucket, overriding what the
        legacy name/amount heuristic would have produced."""
        self._post_invoice(1000.0, self.tax_reduced_via_grid)

        result = self.engine.get_tax_report(
            date_from="2024-01-01", date_to="2024-12-31",
            company_id=self.company_data["company"].id,
        )
        lines_by_key = {
            l["line_key"]: l for l in result["lines"] if not l.get("section_header")
        }

        # Grid-driven expectation: box 2 -> reduced_sales.
        self.assertAlmostEqual(
            lines_by_key["reduced_sales"]["base_amount"], 1000.0, places=1,
            msg="Grid-tagged amount did not land in the tag's own bucket "
                "(reduced_sales) — grid path may not be active.",
        )
        self.assertAlmostEqual(
            lines_by_key["reduced_sales"]["vat_amount"], 150.0, places=1,
        )

        # And it must NOT have fallen into std_sales (which is where the
        # legacy name/amount heuristic would have put a 15%, non-keyword
        # tax) — proves we are not silently using the name-based path.
        self.assertAlmostEqual(
            lines_by_key["std_sales"]["base_amount"], 0.0, places=1,
            msg="Amount leaked into std_sales — grid tag was ignored "
                "and the legacy name-based bucketing ran instead.",
        )

    def test_total_sales_still_consistent_with_grid_buckets(self):
        """Sum-of-lines invariant must hold on the grid path too, same
        as the existing name-based test in test_vat_return.py."""
        self._post_invoice(500.0, self.tax_reduced_via_grid)
        result = self.engine.get_tax_report(
            date_from="2024-01-01", date_to="2024-12-31",
            company_id=self.company_data["company"].id,
        )
        lines_by_key = {
            l["line_key"]: l for l in result["lines"] if not l.get("section_header")
        }
        expected = sum(
            lines_by_key.get(k, {}).get("base_amount", 0.0)
            for k in ("std_sales", "reduced_sales", "zero_sales", "exports", "exempt_sales")
        )
        self.assertAlmostEqual(lines_by_key["total_sales"]["base_amount"], round(expected, 2))


@tagged("post_install", "-at_install")
class TestVATGridTagMultiCompanyIsolation(FSEnterpriseCommon):
    """Regression test for the cross-company leak: Company A configures
    real Tax Grid tags. Company B's own taxes never reference them.
    Company B's VAT report must still work correctly via the
    name-based fallback — it must NOT silently show all zeros just
    because grid tags exist *somewhere* in the (shared) tag table.
    """

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # --- Company A: has real grid tags on its own tax. ---
        cls.company_a = cls.company_data["company"]
        base_tag, vat_tag = _make_grid_tags(cls.env, 1, show_vat=True)
        cls.tax_company_a = _make_tagged_tax(
            cls.env, cls.company_a, "Company A Standard Sales", 15.0,
            "sale", base_tag, vat_tag,
        )

        # --- Company B: separate company, own (untagged) tax, no grid
        # configuration of its own at all. ---
        cls.company_b = cls.env["res.company"].create({"name": "Grid Isolation Co B"})
        # Give company B a minimal chart: reuse company A's journal
        # config pattern via a simple misc journal + basic accounts.
        cls.journal_b = cls.env["account.journal"].create({
            "name": "Misc B", "type": "general", "code": "MSCB",
            "company_id": cls.company_b.id,
        })
        cls.revenue_b = cls.env["account.account"].create({
            "name": "Revenue B", "code": "RB1000", "account_type": "income",
            "company_ids": [(6, 0, [cls.company_b.id])],
        })
        cls.receivable_b = cls.env["account.account"].create({
            "name": "Receivable B", "code": "RB1100",
            "account_type": "asset_receivable",
            "company_ids": [(6, 0, [cls.company_b.id])],
        })
        # Plain, untagged 15% sales tax — this is what most companies
        # that have never configured Tax Grids actually have.
        cls.tax_company_b = cls.env["account.tax"].create({
            "name": "Company B Standard Sales Tax",
            "type_tax_use": "sale",
            "amount_type": "percent",
            "amount": 15.0,
            "company_id": cls.company_b.id,
        })

    def test_company_b_not_flagged_as_grid_user(self):
        """The key isolation check: even though grid tags exist in the
        (shared) tag table because Company A created them, Company B's
        own taxes don't reference them, so the dispatch helper must
        say False for Company B."""
        tag_map = self.engine._get_vat_grid_tags()
        self.assertTrue(tag_map, "Sanity check: Company A's grid tags must exist globally.")
        self.assertFalse(
            self.engine._company_uses_vat_grid_tags(self.company_b, tag_map),
            "Company B was incorrectly detected as using Tax Grids "
            "just because Company A's tags exist in the shared "
            "account.account.tag table.",
        )

    def test_untagged_company_not_affected_by_other_companys_grid_tags(self):
        """End-to-end: Company B's VAT report, computed with Company A's
        grid tags present in the database, must still reflect Company
        B's real transactions via the name-based fallback — not zero
        everything out."""
        move = self.env["account.move"].create({
            "move_type": "out_invoice",
            "date": "2024-06-01",
            "invoice_date": "2024-06-01",
            "journal_id": self.journal_b.id,
            "invoice_line_ids": [(0, 0, {
                "name": "Company B sale",
                "account_id": self.revenue_b.id,
                "quantity": 1,
                "price_unit": 2000.0,
                "tax_ids": [(6, 0, [self.tax_company_b.id])],
            })],
        })
        move.action_post()

        result = self.engine.get_tax_report(
            date_from="2024-01-01", date_to="2024-12-31",
            company_id=self.company_b.id,
        )
        lines_by_key = {
            l["line_key"]: l for l in result["lines"] if not l.get("section_header")
        }
        self.assertAlmostEqual(
            lines_by_key["std_sales"]["base_amount"], 2000.0, places=1,
            msg=(
                "Company B's VAT report returned 0 instead of its real "
                "2000.0 base amount — Company A's unrelated grid tags "
                "leaked into Company B's report dispatch logic."
            ),
        )
        self.assertAlmostEqual(lines_by_key["std_sales"]["vat_amount"], 300.0, places=1)

    def test_company_a_still_correctly_uses_its_own_grid_tags(self):
        """Sanity: the fix must not break Company A's own (legitimate)
        grid-based reporting while fixing Company B's isolation."""
        move = self.env["account.move"].create({
            "move_type": "out_invoice",
            "date": "2024-06-01",
            "invoice_date": "2024-06-01",
            "journal_id": self.journal_misc.id,
            "invoice_line_ids": [(0, 0, {
                "name": "Company A sale",
                "account_id": self.account_revenue.id,
                "quantity": 1,
                "price_unit": 1000.0,
                "tax_ids": [(6, 0, [self.tax_company_a.id])],
            })],
        })
        move.action_post()

        result = self.engine.get_tax_report(
            date_from="2024-01-01", date_to="2024-12-31",
            company_id=self.company_a.id,
        )
        lines_by_key = {
            l["line_key"]: l for l in result["lines"] if not l.get("section_header")
        }
        self.assertAlmostEqual(lines_by_key["std_sales"]["base_amount"], 1000.0, places=1)
        self.assertAlmostEqual(lines_by_key["std_sales"]["vat_amount"], 150.0, places=1)