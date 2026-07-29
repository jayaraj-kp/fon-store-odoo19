# Copyright 2024 Custom Development
# License: LGPL-3.0 or later

from odoo import api, models


class ReportFinancialStatement(models.AbstractModel):
    # Keep _name short: PostgreSQL limits identifiers to 63 chars.
    _name = "report.oca_financial_statements_enterprise_view.fs_pdf"
    _description = "Financial Statement PDF Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        report_type = data.get("report_type", "bs")
        title = "Balance Sheet" if report_type == "bs" else "Profit and Loss"
        return {
            "doc_ids": docids,
            "doc_model": "financial.report.engine",
            "lines": data.get("lines", []),
            "report_type": report_type,
            "report_title": title,
            "company_name": data.get("company_name", ""),
            "currency_symbol": data.get("currency_symbol", ""),
            "date_from": data.get("date_from", ""),
            "date_to": data.get("date_to", ""),
        }
