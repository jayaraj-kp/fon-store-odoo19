# Copyright 2024 Custom Development
# License: LGPL-3.0 or later

import base64
import datetime
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class OcaFinancialStatementsController(http.Controller):
    """JSON controller for Enterprise-style Balance Sheet & P&L OWL views."""

    def _engine(self):
        return request.env["financial.report.engine"]

    # ------------------------------------------------------------------
    # /oca_fs/init
    # ------------------------------------------------------------------
    @http.route("/oca_fs/init", type="json", auth="user")
    def get_init_data(self, company_id=None):
        env = request.env
        company = (
            env["res.company"].browse(int(company_id))
            if company_id
            else env.company
        )
        companies = env["res.company"].search_read(
            [("id", "in", env.user.company_ids.ids)],
            ["id", "name"],
            order="name",
        )
        today = datetime.date.today()
        date_from = today.replace(month=1, day=1).isoformat()
        date_to = today.isoformat()

        return {
            "companies": companies,
            "company_id": company.id,
            "company_name": company.name,
            "currency_name": company.currency_id.name,
            "currency_symbol": company.currency_id.symbol,
            "date_from": date_from,
            "date_to": date_to,
        }

    # ------------------------------------------------------------------
    # /oca_fs/get_data
    # ------------------------------------------------------------------
    @http.route("/oca_fs/get_data", type="json", auth="user")
    def get_data(
        self,
        report_type,
        date_from=None,
        date_to=None,
        company_id=None,
        target_move="posted",
        comparison_mode="none",
        comparison_date_from=None,
        comparison_date_to=None,
        comparison_periods=None,
        **kwargs,
    ):
        engine = self._engine()
        company = (
            request.env["res.company"].browse(int(company_id))
            if company_id
            else request.env.company
        )

        if not date_to:
            date_to = datetime.date.today().isoformat()

        if report_type == "bs":
            result = engine.get_balance_sheet(
                date_to=date_to,
                company_id=company.id,
                target_move=target_move,
            )
            if comparison_mode not in ("none", "percentage_of") and comparison_periods:
                comp_periods = []
                for period in comparison_periods:
                    comp_date_to = period.get("date_to")
                    if not comp_date_to:
                        continue
                    comp = engine.get_balance_sheet(
                        date_to=comp_date_to,
                        company_id=company.id,
                        target_move=target_move,
                    )
                    comp_periods.append(
                        {
                            "label": period.get("label", ""),
                            "date_to": comp_date_to,
                            "date_from": period.get("date_from", ""),
                            "lines": comp["lines"],
                        }
                    )
                if comp_periods:
                    result["lines"] = engine.merge_multi_comparison_lines(
                        result["lines"], comp_periods
                    )
                    result["comparison_columns"] = [
                        {"label": p["label"], "date_to": p["date_to"]}
                        for p in comp_periods
                    ]
            elif comparison_mode not in ("none", "percentage_of") and comparison_date_to:
                comp = engine.get_balance_sheet(
                    date_to=comparison_date_to,
                    company_id=company.id,
                    target_move=target_move,
                )
                result["lines"] = engine.merge_comparison_lines(
                    result["lines"], comp["lines"]
                )
        else:
            if not date_from:
                date_from = datetime.date.today().replace(month=1, day=1).isoformat()
            result = engine.get_profit_and_loss(
                date_from=date_from,
                date_to=date_to,
                company_id=company.id,
                target_move=target_move,
            )
            if comparison_mode not in ("none", "percentage_of") and comparison_periods:
                comp_periods = []
                for period in comparison_periods:
                    p_from = period.get("date_from")
                    p_to = period.get("date_to")
                    if not p_from or not p_to:
                        continue
                    comp = engine.get_profit_and_loss(
                        date_from=p_from,
                        date_to=p_to,
                        company_id=company.id,
                        target_move=target_move,
                    )
                    comp_periods.append(
                        {
                            "label": period.get("label", ""),
                            "date_to": p_to,
                            "date_from": p_from,
                            "lines": comp["lines"],
                        }
                    )
                if comp_periods:
                    result["lines"] = engine.merge_multi_comparison_lines(
                        result["lines"], comp_periods
                    )
                    result["comparison_columns"] = [
                        {"label": p["label"], "date_to": p["date_to"]}
                        for p in comp_periods
                    ]
            elif (
                comparison_mode not in ("none", "percentage_of")
                and comparison_date_from
                and comparison_date_to
            ):
                comp = engine.get_profit_and_loss(
                    date_from=comparison_date_from,
                    date_to=comparison_date_to,
                    company_id=company.id,
                    target_move=target_move,
                )
                result["lines"] = engine.merge_comparison_lines(
                    result["lines"], comp["lines"]
                )

        result["has_unposted"] = engine.has_unposted_entries(
            date_to=date_to, company_id=company.id
        )
        result["report_type"] = report_type
        return result

    # ------------------------------------------------------------------
    # /oca_fs/export_pdf
    # ------------------------------------------------------------------
    @http.route("/oca_fs/export_pdf", type="json", auth="user")
    def export_pdf(
        self,
        report_type,
        date_from=None,
        date_to=None,
        company_id=None,
        target_move="posted",
        **kwargs,
    ):
        data = self.get_data(
            report_type=report_type,
            date_from=date_from,
            date_to=date_to,
            company_id=company_id,
            target_move=target_move,
        )
        report_xmlid = (
            "oca_financial_statements_enterprise_view.report_financial_statement_pdf"
        )
        pdf_content, _ = request.env["ir.actions.report"]._render_qweb_pdf(
            report_xmlid,
            res_ids=[],
            data={
                "report_type": report_type,
                "lines": data.get("lines", []),
                "company_name": data.get("company_name"),
                "currency_symbol": data.get("currency_symbol"),
                "date_from": data.get("date_from"),
                "date_to": data.get("date_to"),
            },
        )
        title = "Balance_Sheet" if report_type == "bs" else "Profit_and_Loss"
        return {
            "file_content": base64.b64encode(pdf_content).decode("utf-8"),
            "file_name": f"{title}_{date_to or 'report'}.pdf",
        }
