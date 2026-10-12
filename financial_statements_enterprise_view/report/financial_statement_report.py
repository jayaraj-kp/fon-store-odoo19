# Copyright 2024 Custom Development
# License: LGPL-3.0 or later

from odoo import api, models


class ReportFinancialStatement(models.AbstractModel):
    # Keep _name short: PostgreSQL limits identifiers to 63 chars.
    _name = "report.financial_statements_enterprise_view.fs_pdf"
    _description = "Financial Statement PDF Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        report_type = data.get("report_type", "bs")
        title = "Balance Sheet" if report_type == "bs" else "Profit and Loss"
        # FIX (multi-company): hand the template the company the report was
        # computed for, so the header (name/logo/VAT) matches the figures even
        # when it is not the user's active company. ``data`` can reach this
        # model through the generic /report/pdf route, so only honour a
        # company the current user is actually allowed to access.
        company = self.env.company
        try:
            requested_id = int(data.get("company_id") or 0)
        except (TypeError, ValueError):
            requested_id = 0
        if requested_id and requested_id in self.env.user.company_ids.ids:
            company = self.env["res.company"].browse(requested_id)
        return {
            "company": company,
            "doc_ids": docids,
            "doc_model": "financial.report.engine",
            "lines": data.get("lines", []),
            "report_type": report_type,
            "report_title": title,
            "company_name": data.get("company_name", ""),
            "currency_symbol": data.get("currency_symbol", ""),
            "currency_digits": data.get("currency_digits", 2),
            "date_from": data.get("date_from", ""),
            "date_to": data.get("date_to", ""),
            "with_debit_credit": data.get("with_debit_credit", False),
            # FIX (#6): these were silently dropped before, so the PDF
            # template never saw comparison data even though the controller
            # computed it.
            "comparison_columns": data.get("comparison_columns", []),
            "analytic_columns": data.get("analytic_columns", []),
            # FIX (#7): pass through so the template can switch to RTL.
            "is_rtl": data.get("is_rtl", False),
            "report_lang": data.get("report_lang", "en_US"),
        }