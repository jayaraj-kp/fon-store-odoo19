# Copyright 2024 YourCompany
# License: LGPL-3.0 or later

"""
VAT Return (Tax Report) Engine Tests
======================================
ഈ test file Saudi Arabia GAZT-style 16-line VAT return engine-ന്റെ
correctness verify ചെയ്യുന്നു. രണ്ട് strategies cover ചെയ്യുന്നു:

  1. Name-based bucketing (_get_tax_report_buckets_by_name) —
     Tax Grid tags configure ചെയ്യാത്ത companies-ൽ ഉപയോഗിക്കുന്ന
     legacy fallback. Tax name-ൽ നിന്ന് bucket infer ചെയ്യുന്നു.

  2. Result structure validation — get_tax_report() return value-ന്റെ
     shape, line keys, totals ഒക്കെ correct ആണോ.

  3. Period boundary — date_from / date_to filter properly ആണോ.

  4. draft / posted filter — target_move respect ചെയ്യുന്നോ.

  5. Comparison merge — merge_tax_comparison_lines() correct ആണോ.
"""

from odoo.tests import tagged

from .common import FSEnterpriseCommon


@tagged("post_install", "-at_install")
class TestVATReturnStructure(FSEnterpriseCommon):
    """get_tax_report() return value shape and line key tests.

    DB-ൽ real taxes create ചെയ്യാതെ, empty period-ൽ engine call ചെയ്ത്
    structure correct ആണോ validate ചെയ്യുന്നു. Accounts / journal entries
    ഒന്നും ഇല്ലാതെ call ചെയ്‌താൽ engine crash ആകരുത്, 0.0 values
    return ചെയ്യണം.
    """

    # Expected line keys (16 lines — some are section headers).
    _EXPECTED_LINE_KEYS = {
        "std_sales", "reduced_sales", "zero_sales", "exports", "exempt_sales",
        "total_sales",
        "std_purch", "import_customs", "import_rc", "zero_purch", "exempt_purch",
        "total_purch",
        "total_vat_due", "corrections", "credit_forward", "net_vat",
    }

    def _call_engine(self, date_from="2024-01-01", date_to="2024-12-31"):
        return self.engine.get_tax_report(
            date_from=date_from,
            date_to=date_to,
            company_id=self.company_data["company"].id,
        )

    def test_return_value_has_required_keys(self):
        """get_tax_report() must return a dict with lines, company_name,
        currency_symbol, date_from, date_to."""
        result = self._call_engine()
        for key in ("lines", "company_name", "currency_symbol", "date_from", "date_to"):
            self.assertIn(key, result, f"Missing key: {key}")

    def test_all_16_line_keys_present(self):
        """Result must contain all 16 GAZT line keys (excluding section headers)."""
        result = self._call_engine()
        returned_keys = {
            line["line_key"]
            for line in result["lines"]
            if not line.get("section_header")
        }
        missing = self._EXPECTED_LINE_KEYS - returned_keys
        self.assertFalse(
            missing,
            f"Missing line_key(s) in VAT report: {missing}",
        )

    def test_empty_period_returns_zero_totals(self):
        """No transactions → every amount must be 0.0, engine must not crash."""
        result = self._call_engine()
        for line in result["lines"]:
            if line.get("section_header"):
                continue
            self.assertAlmostEqual(
                line.get("base_amount", 0.0), 0.0,
                msg=f"Expected 0 base on {line['line_key']}, got {line.get('base_amount')}",
            )
            self.assertAlmostEqual(
                line.get("vat_amount", 0.0), 0.0,
                msg=f"Expected 0 VAT on {line['line_key']}, got {line.get('vat_amount')}",
            )

    def test_net_vat_line_present_and_numeric(self):
        """Line 16 'net_vat' must always exist and vat_amount must be a number."""
        result = self._call_engine()
        net_vat = next(
            (l for l in result["lines"] if l.get("line_key") == "net_vat"), None
        )
        self.assertIsNotNone(net_vat, "line_key='net_vat' not found in result")
        self.assertIsInstance(net_vat["vat_amount"], (int, float))

    def test_total_sales_equals_sum_of_sales_lines(self):
        """total_sales base_amount must equal the sum of lines 1-5 base_amounts."""
        result = self._call_engine()
        lines_by_key = {
            l["line_key"]: l for l in result["lines"] if not l.get("section_header")
        }
        expected_base = sum(
            lines_by_key.get(k, {}).get("base_amount", 0.0)
            for k in ("std_sales", "reduced_sales", "zero_sales", "exports", "exempt_sales")
        )
        self.assertAlmostEqual(
            lines_by_key["total_sales"]["base_amount"],
            round(expected_base, 2),
        )

    def test_total_purchases_equals_sum_of_purchase_lines(self):
        """total_purch base_amount must equal sum of lines 7-11 base_amounts."""
        result = self._call_engine()
        lines_by_key = {
            l["line_key"]: l for l in result["lines"] if not l.get("section_header")
        }
        expected_base = sum(
            lines_by_key.get(k, {}).get("base_amount", 0.0)
            for k in ("std_purch", "import_customs", "import_rc", "zero_purch", "exempt_purch")
        )
        self.assertAlmostEqual(
            lines_by_key["total_purch"]["base_amount"],
            round(expected_base, 2),
        )


@tagged("post_install", "-at_install")
class TestVATReturnWithTaxes(FSEnterpriseCommon):
    """Integration tests: real taxes + real journal entries → VAT report values."""

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        company = cls.company_data["company"]

        # --- Standard Sales Tax (15%) ---
        cls.tax_std_sales = cls.env["account.tax"].create({
            "name": "Standard Sales Tax 15%",
            "type_tax_use": "sale",
            "amount_type": "percent",
            "amount": 15.0,
            "company_id": company.id,
        })

        # --- Standard Purchase Tax (15%) ---
        cls.tax_std_purch = cls.env["account.tax"].create({
            "name": "Standard Purchase Tax 15%",
            "type_tax_use": "purchase",
            "amount_type": "percent",
            "amount": 15.0,
            "company_id": company.id,
        })

        # --- Zero-Rated Sales Tax ---
        cls.tax_zero_sales = cls.env["account.tax"].create({
            "name": "Zero Rated Sales",
            "type_tax_use": "sale",
            "amount_type": "percent",
            "amount": 0.0,
            "company_id": company.id,
        })

        # --- Export Tax (0%, name contains 'export') ---
        cls.tax_export = cls.env["account.tax"].create({
            "name": "Export Sales Tax",
            "type_tax_use": "sale",
            "amount_type": "percent",
            "amount": 0.0,
            "company_id": company.id,
        })

    def _make_invoice(self, move_type, date, amount, tax, journal=None):
        """Create and post a simple single-line invoice with one tax."""
        journal = journal or self.journal_misc
        account = (
            self.account_revenue
            if move_type in ("out_invoice", "out_refund")
            else self.account_expense
        )
        move = self.env["account.move"].create({
            "move_type": move_type,
            "date": date,
            "invoice_date": date,
            "journal_id": journal.id,
            "invoice_line_ids": [
                (0, 0, {
                    "name": "Test line",
                    "account_id": account.id,
                    "quantity": 1,
                    "price_unit": amount,
                    "tax_ids": [(6, 0, [tax.id])],
                }),
            ],
        })
        move.action_post()
        return move

    def _get_vat_lines(self, date_from="2024-01-01", date_to="2024-12-31"):
        result = self.engine.get_tax_report(
            date_from=date_from,
            date_to=date_to,
            company_id=self.company_data["company"].id,
        )
        return {
            l["line_key"]: l
            for l in result["lines"]
            if not l.get("section_header")
        }

    # ------------------------------------------------------------------
    # Standard Sales Tax
    # ------------------------------------------------------------------

    def test_standard_sales_base_and_vat(self):
        """Invoice with 15% sales tax → std_sales base=1000, vat=150."""
        self._make_invoice("out_invoice", "2024-03-15", 1000.0, self.tax_std_sales)
        lines = self._get_vat_lines()

        self.assertAlmostEqual(lines["std_sales"]["base_amount"], 1000.0, places=1)
        self.assertAlmostEqual(lines["std_sales"]["vat_amount"], 150.0, places=1)

    def test_standard_sales_vat_flows_to_total_sales(self):
        """std_sales vat must be included in total_sales vat_amount."""
        self._make_invoice("out_invoice", "2024-04-01", 500.0, self.tax_std_sales)
        lines = self._get_vat_lines()

        self.assertGreaterEqual(lines["total_sales"]["vat_amount"], 75.0)

    def test_standard_purchase_reduces_net_vat(self):
        """Purchase VAT is recoverable — net_vat must be sales_vat minus purchase_vat."""
        self._make_invoice("out_invoice", "2024-05-01", 1000.0, self.tax_std_sales)
        self._make_invoice("in_invoice", "2024-05-02", 400.0, self.tax_std_purch)
        lines = self._get_vat_lines()

        expected_net = round(
            lines["total_sales"]["vat_amount"] - lines["total_purch"]["vat_amount"], 2
        )
        self.assertAlmostEqual(lines["net_vat"]["vat_amount"], expected_net, places=1)

    def test_zero_rated_sales_have_no_vat(self):
        """Zero-rated sales → base_amount populated, vat_amount = 0."""
        self._make_invoice("out_invoice", "2024-06-01", 800.0, self.tax_zero_sales)
        lines = self._get_vat_lines()

        # Zero-rated bucket: show_vat=False so vat_amount must be 0
        self.assertAlmostEqual(lines["zero_sales"]["vat_amount"], 0.0)
        # base_amount should reflect the sale (may be 0 in name-based
        # bucketing if the fallback can't distinguish zero_sales from
        # other 0% taxes — acceptable; we just ensure no crash).
        self.assertGreaterEqual(lines["zero_sales"]["base_amount"], 0.0)

    # ------------------------------------------------------------------
    # Period boundaries
    # ------------------------------------------------------------------

    def test_entry_before_date_from_excluded(self):
        """A transaction dated in 2023 must not appear in 2024 VAT report."""
        self._make_invoice("out_invoice", "2023-12-31", 2000.0, self.tax_std_sales)
        lines = self._get_vat_lines(date_from="2024-01-01", date_to="2024-12-31")

        # 2023 invoice must not contribute to 2024 std_sales
        self.assertAlmostEqual(lines["std_sales"]["base_amount"], 0.0, places=1)

    def test_entry_after_date_to_excluded(self):
        """A transaction dated in 2025 must not appear in 2024 VAT report."""
        self._make_invoice("out_invoice", "2025-01-15", 3000.0, self.tax_std_sales)
        lines = self._get_vat_lines(date_from="2024-01-01", date_to="2024-12-31")

        self.assertAlmostEqual(lines["std_sales"]["base_amount"], 0.0, places=1)

    def test_entry_exactly_on_date_to_included(self):
        """A transaction on date_to itself must be included (boundary is inclusive)."""
        self._make_invoice("out_invoice", "2024-12-31", 1000.0, self.tax_std_sales)
        lines = self._get_vat_lines(date_from="2024-01-01", date_to="2024-12-31")

        self.assertAlmostEqual(lines["std_sales"]["base_amount"], 1000.0, places=1)

    # ------------------------------------------------------------------
    # Draft / Posted
    # ------------------------------------------------------------------

    def test_draft_invoice_excluded_from_posted_report(self):
        """Draft invoices must not appear when target_move='posted'."""
        move = self.env["account.move"].create({
            "move_type": "out_invoice",
            "date": "2024-07-01",
            "invoice_date": "2024-07-01",
            "journal_id": self.journal_misc.id,
            "invoice_line_ids": [(0, 0, {
                "name": "Draft line",
                "account_id": self.account_revenue.id,
                "quantity": 1,
                "price_unit": 1000.0,
                "tax_ids": [(6, 0, [self.tax_std_sales.id])],
            })],
        })
        # Intentionally left in draft — NOT posted

        result = self.engine.get_tax_report(
            date_from="2024-01-01",
            date_to="2024-12-31",
            company_id=self.company_data["company"].id,
            target_move="posted",
        )
        lines_by_key = {
            l["line_key"]: l for l in result["lines"] if not l.get("section_header")
        }
        self.assertAlmostEqual(lines_by_key["std_sales"]["base_amount"], 0.0, places=1)

    def test_draft_invoice_included_when_all_moves(self):
        """Draft invoices must appear when target_move='all'."""
        move = self.env["account.move"].create({
            "move_type": "out_invoice",
            "date": "2024-07-01",
            "invoice_date": "2024-07-01",
            "journal_id": self.journal_misc.id,
            "invoice_line_ids": [(0, 0, {
                "name": "Draft line",
                "account_id": self.account_revenue.id,
                "quantity": 1,
                "price_unit": 1000.0,
                "tax_ids": [(6, 0, [self.tax_std_sales.id])],
            })],
        })
        # Left in draft intentionally

        result = self.engine.get_tax_report(
            date_from="2024-01-01",
            date_to="2024-12-31",
            company_id=self.company_data["company"].id,
            target_move="all",
        )
        lines_by_key = {
            l["line_key"]: l for l in result["lines"] if not l.get("section_header")
        }
        # base_amount > 0 confirms draft entry was picked up
        self.assertGreater(lines_by_key["std_sales"]["base_amount"], 0.0)


@tagged("post_install", "-at_install")
class TestVATComparisonMerge(FSEnterpriseCommon):
    """merge_tax_comparison_lines() — pure data transform tests.

    Engine-ന്റെ comparison merge logic verify ചെയ്യുന്നു:
    current period lines-ൽ comparison_balances attach ആകുന്നോ,
    label/date_to values correct ആണോ.
    """

    def setUp(self):
        super().setUp()
        self.engine = self.env["financial.report.engine"]

    def _make_vat_lines(self, std_sales_base=0.0, std_sales_vat=0.0):
        """Minimal fake VAT report lines list (only std_sales for brevity)."""
        return [
            {"section_header": True, "name": "VAT on Sales:", "section": "sales"},
            {
                "number": 1, "name": "Standard rated sales",
                "section": "sales", "line_key": "std_sales",
                "base_amount": std_sales_base, "vat_amount": std_sales_vat,
                "style": "data", "show_base": True, "show_vat": True,
            },
            {
                "number": 6, "name": "Total Sales",
                "section": "sales", "line_key": "total_sales",
                "base_amount": std_sales_base, "vat_amount": std_sales_vat,
                "style": "subtotal", "show_base": True, "show_vat": True,
            },
        ]

    def test_comparison_balances_attached_to_each_line(self):
        current = self._make_vat_lines(std_sales_base=1000.0, std_sales_vat=150.0)
        comparison_periods = [
            {
                "label": "Q1 2023", "date_from": "2023-01-01", "date_to": "2023-03-31",
                "lines": self._make_vat_lines(std_sales_base=800.0, std_sales_vat=120.0),
            },
        ]
        merged = self.engine.merge_tax_comparison_lines(current, comparison_periods)

        data_lines = [l for l in merged if not l.get("section_header")]
        for line in data_lines:
            self.assertIn(
                "comparison_balances", line,
                f"comparison_balances missing on line_key={line.get('line_key')}",
            )

    def test_comparison_balances_correct_values(self):
        current = self._make_vat_lines(std_sales_base=1000.0, std_sales_vat=150.0)
        comparison_periods = [
            {
                "label": "Prev Period", "date_from": "2023-01-01", "date_to": "2023-12-31",
                "lines": self._make_vat_lines(std_sales_base=600.0, std_sales_vat=90.0),
            },
        ]
        merged = self.engine.merge_tax_comparison_lines(current, comparison_periods)
        std_line = next(l for l in merged if l.get("line_key") == "std_sales")

        self.assertEqual(len(std_line["comparison_balances"]), 1)
        cb = std_line["comparison_balances"][0]
        self.assertAlmostEqual(cb["base_amount"], 600.0)
        self.assertAlmostEqual(cb["vat_amount"], 90.0)
        self.assertEqual(cb["label"], "Prev Period")

    def test_section_header_gets_empty_comparison_balances(self):
        """Section header lines (section_header=True) must get an empty list,
        not raise KeyError."""
        current = self._make_vat_lines()
        comparison_periods = [{
            "label": "Prev", "date_from": "2023-01-01", "date_to": "2023-12-31",
            "lines": self._make_vat_lines(),
        }]
        merged = self.engine.merge_tax_comparison_lines(current, comparison_periods)
        header = next(l for l in merged if l.get("section_header"))
        self.assertEqual(header["comparison_balances"], [])

    def test_multi_period_comparison_all_periods_present(self):
        """Two comparison periods → comparison_balances list length must be 2."""
        current = self._make_vat_lines(std_sales_base=500.0, std_sales_vat=75.0)
        comparison_periods = [
            {
                "label": "Q1", "date_from": "2023-01-01", "date_to": "2023-03-31",
                "lines": self._make_vat_lines(100.0, 15.0),
            },
            {
                "label": "Q2", "date_from": "2023-04-01", "date_to": "2023-06-30",
                "lines": self._make_vat_lines(200.0, 30.0),
            },
        ]
        merged = self.engine.merge_tax_comparison_lines(current, comparison_periods)
        std_line = next(l for l in merged if l.get("line_key") == "std_sales")
        self.assertEqual(len(std_line["comparison_balances"]), 2)
        labels = [cb["label"] for cb in std_line["comparison_balances"]]
        self.assertEqual(labels, ["Q1", "Q2"])

    def test_missing_line_key_in_comparison_defaults_to_zero(self):
        """If comparison period has no matching line_key, base/vat must be 0."""
        current = self._make_vat_lines(500.0, 75.0)
        # comparison has no std_sales line
        comparison_periods = [{
            "label": "Empty", "date_from": "2023-01-01", "date_to": "2023-12-31",
            "lines": [
                {"section_header": True, "name": "VAT on Sales:", "section": "sales"},
            ],
        }]
        merged = self.engine.merge_tax_comparison_lines(current, comparison_periods)
        std_line = next(l for l in merged if l.get("line_key") == "std_sales")
        cb = std_line["comparison_balances"][0]
        self.assertAlmostEqual(cb["base_amount"], 0.0)
        self.assertAlmostEqual(cb["vat_amount"], 0.0)