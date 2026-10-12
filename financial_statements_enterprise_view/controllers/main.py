# Copyright 2024 YourCompany
# License: LGPL-3.0 or later

import base64
import datetime
import io
import logging

from odoo import http, _
from odoo.exceptions import AccessError
from odoo.http import request

_logger = logging.getLogger(__name__)


class FinancialStatementsEnterpriseController(http.Controller):
    """JSON controller for Enterprise-style Balance Sheet, P&L and VAT OWL views."""

    # FIX (perf/safety): hard ceiling on how many comparison periods a
    # single request can ask for. Each period re-runs a full balance
    # computation server-side, so an unbounded list (buggy client, direct
    # API call, etc.) could turn one HTTP request into dozens of queries.
    # The UI never needs more than a handful of comparison columns, so
    # this does not change any existing behavior.
    _MAX_COMPARISON_PERIODS = 12

    # FIX (perf/safety): same reasoning as _MAX_COMPARISON_PERIODS above,
    # but for analytic_account_ids. get_data() re-runs a full balance
    # sheet / P&L computation *per selected analytic account* to build
    # the per-analytic-account columns (see the "Analytic column
    # generation" block below). Without a cap, a client could pass in
    # hundreds/thousands of analytic account ids and turn one HTTP
    # request into hundreds of extra full aggregation queries — a real
    # DoS/performance risk once a company has a large analytic chart.
    # The UI only ever offers a manageable number of columns anyway.
    _MAX_ANALYTIC_ACCOUNTS = 20

    def _engine(self):
        return request.env["financial.report.engine"]

    def _cap_comparison_periods(self, comparison_periods):
        if not comparison_periods:
            return comparison_periods
        if len(comparison_periods) > self._MAX_COMPARISON_PERIODS:
            _logger.warning(
                "comparison_periods truncated from %s to %s entries",
                len(comparison_periods), self._MAX_COMPARISON_PERIODS,
            )
            return comparison_periods[: self._MAX_COMPARISON_PERIODS]
        return comparison_periods

    def _cap_analytic_accounts(self, analytic_account_ids):
        if not analytic_account_ids:
            return analytic_account_ids
        if len(analytic_account_ids) > self._MAX_ANALYTIC_ACCOUNTS:
            _logger.warning(
                "analytic_account_ids truncated from %s to %s entries",
                len(analytic_account_ids), self._MAX_ANALYTIC_ACCOUNTS,
            )
            return analytic_account_ids[: self._MAX_ANALYTIC_ACCOUNTS]
        return analytic_account_ids

    def _check_account_group(self):
        # AbstractModel has no ACL - enforce at controller layer
        if not request.env.user.has_group("account.group_account_user"):
            raise AccessError(_("You do not have access to financial reports. Accounting access required."))

    # ------------------------------------------------------------------
    # /fs_enterprise/init
    # ------------------------------------------------------------------
    @http.route("/fs_enterprise/init", type="json", auth="user")
    def get_init_data(self, company_id=None):
        self._check_account_group()
        env = request.env
        if company_id and int(company_id) not in env.user.company_ids.ids:
            raise AccessError(_("You do not have access to this company's data."))
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
            "currency_digits": company.currency_id.decimal_places if company.currency_id else 2,
            "date_from": date_from,
            "date_to": date_to,
            "fiscalyear_last_day": company.fiscalyear_last_day or 31,
            "fiscalyear_last_month": int(company.fiscalyear_last_month or "12"),
        }

    # ------------------------------------------------------------------
    # /fs_enterprise/get_data
    # ------------------------------------------------------------------
    @http.route("/fs_enterprise/get_data", type="json", auth="user")
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
        analytic_account_ids=None,
        with_debit_credit=False,
        include_unassigned=False,
        **kwargs,
    ):
        self._check_account_group()
        engine = self._engine()
        company = (
            request.env["res.company"].browse(int(company_id))
            if company_id
            else request.env.company
        )

        # FIX: validate the company belongs to the requesting user rather
        # than trusting the client-supplied id blindly.
        if company_id and int(company_id) not in request.env.user.company_ids.ids:
            raise AccessError(_("You do not have access to this company's data."))

        comparison_periods = self._cap_comparison_periods(comparison_periods)
        # FIX: cap analytic_account_ids too — see _MAX_ANALYTIC_ACCOUNTS.
        analytic_account_ids = self._cap_analytic_accounts(analytic_account_ids)

        if not date_to:
            date_to = datetime.date.today().isoformat()

        # Analytic columns (and/or the Unassigned column) are a separate,
        # self-contained code path: comparison / debit-credit are not
        # combined with them, so we do not even compute them.
        if analytic_account_ids or include_unassigned:
            if comparison_mode not in ("none", "percentage_of") or with_debit_credit:
                _logger.info("comparison/debit-credit ignored while analytic columns are active")
            return engine.get_analytic_report(
                report_type, date_from, date_to, company.id, target_move,
                analytic_account_ids, include_unassigned,
            )

        if report_type == "bs":
            result = engine.get_balance_sheet(
                date_to=date_to,
                company_id=company.id,
                target_move=target_move,
                analytic_account_ids=analytic_account_ids,
                with_debit_credit=with_debit_credit,
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
                        analytic_account_ids=analytic_account_ids,
                    )
                    comp_periods.append({
                        "label": period.get("label", ""),
                        "date_to": comp_date_to,
                        "date_from": period.get("date_from", ""),
                        "lines": comp["lines"],
                    })
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
                and comparison_date_to
            ):
                comp = engine.get_balance_sheet(
                    date_to=comparison_date_to,
                    company_id=company.id,
                    target_move=target_move,
                    analytic_account_ids=analytic_account_ids,
                )
                result["lines"] = engine.merge_comparison_lines(
                    result["lines"], comp["lines"]
                )
                # FIX: single-period comparisons also need a column header
                # so the PDF/screen know what label+date to show.
                result["comparison_columns"] = [
                    {"label": _("Comparison"), "date_to": comparison_date_to}
                ]
        else:
            if not date_from:
                date_from = datetime.date.today().replace(month=1, day=1).isoformat()
            result = engine.get_profit_and_loss(
                date_from=date_from,
                date_to=date_to,
                company_id=company.id,
                target_move=target_move,
                analytic_account_ids=analytic_account_ids,
                with_debit_credit=with_debit_credit,
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
                        analytic_account_ids=analytic_account_ids,
                    )
                    comp_periods.append({
                        "label": period.get("label", ""),
                        "date_to": p_to,
                        "date_from": p_from,
                        "lines": comp["lines"],
                    })
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
                    analytic_account_ids=analytic_account_ids,
                )
                result["lines"] = engine.merge_comparison_lines(
                    result["lines"], comp["lines"]
                )
                # FIX: single-period comparisons also need a column header
                result["comparison_columns"] = [
                    {"label": _("Comparison"), "date_to": comparison_date_to}
                ]

        # FIX: pass date_from for P&L so only in-period unposted entries are flagged
        result["has_unposted"] = engine.has_unposted_entries(
            date_from=date_from if report_type != "bs" else None,
            date_to=date_to,
            company_id=company.id,
        )
        result["report_type"] = report_type
        return result

    # ------------------------------------------------------------------
    # Analytic (warehouse) columns - SQL aggregated, no Python line loop
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # /fs_enterprise/export_pdf
    # FIX: now includes comparison columns in the PDF data
    # ------------------------------------------------------------------
    @http.route("/fs_enterprise/export_pdf", type="json", auth="user")
    def export_pdf(
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
        analytic_account_ids=None,
        with_debit_credit=False,
        include_unassigned=False,
        **kwargs,
    ):
        self._check_account_group()
        # FIX: pass all comparison params so PDF reflects same data as screen
        data = self.get_data(
            report_type=report_type,
            date_from=date_from,
            date_to=date_to,
            company_id=company_id,
            target_move=target_move,
            comparison_mode=comparison_mode,
            comparison_date_from=comparison_date_from,
            comparison_date_to=comparison_date_to,
            comparison_periods=comparison_periods,
            analytic_account_ids=analytic_account_ids,
            with_debit_credit=with_debit_credit,
            include_unassigned=include_unassigned,
        )
        report_xmlid = (
            "financial_statements_enterprise_view.report_financial_statement_pdf"
        )
        report_title = "Balance Sheet" if report_type == "bs" else "Profit and Loss"
        # FIX: detect RTL languages (Arabic etc.) so the PDF template can
        # switch text direction / alignment for Saudi / MENA clients.
        report_lang = request.env.lang or "en_US"
        is_rtl = report_lang.split("_")[0] in ("ar", "he", "fa", "ur")
        # FIX: pass currency_digits for dynamic decimal rendering (BHD/KWD 3 decimals)
        currency_digits = data.get("currency_digits", 2)
        # FIX (multi-company): the PDF layout/header (company name, logo, VAT
        # number) is rendered from env.company. get_data() above has already
        # validated that the requested company belongs to the user, so render
        # the PDF in THAT company's context instead of the user's active one.
        cid = int(company_id) if company_id else request.env.company.id
        report_model = request.env["ir.actions.report"].with_context(
            allowed_company_ids=[cid]
        )
        pdf_content, _report_type = report_model._render_qweb_pdf(
            report_xmlid,
            res_ids=[],
            data={
                "company_id": cid,
                "report_type": report_type,
                "report_title": report_title,
                "lines": data.get("lines", []),
                "company_name": data.get("company_name"),
                "currency_symbol": data.get("currency_symbol"),
                "currency_digits": currency_digits,
                "date_from": data.get("date_from"),
                "date_to": data.get("date_to"),
                "with_debit_credit": with_debit_credit,
                "comparison_columns": data.get("comparison_columns", []),
                "analytic_columns": data.get("analytic_columns", []),
                "is_rtl": is_rtl,
                "report_lang": report_lang,
            },
        )
        title = "Balance_Sheet" if report_type == "bs" else "Profit_and_Loss"
        return {
            "file_content": base64.b64encode(pdf_content).decode("utf-8"),
            "file_name": f"{title}_{date_to or 'report'}.pdf",
        }

    # ------------------------------------------------------------------
    # /fs_enterprise/get_tax_report
    # ------------------------------------------------------------------
    @http.route("/fs_enterprise/get_tax_report", type="json", auth="user")
    def get_tax_report(
        self,
        date_from=None,
        date_to=None,
        company_id=None,
        target_move="posted",
        comparison_periods=None,
        analytic_account_ids=None,
        **kwargs,
    ):
        self._check_account_group()
        if not date_to:
            date_to = datetime.date.today().isoformat()
        if not date_from:
            date_from = datetime.date.today().replace(month=1, day=1).isoformat()

        engine = self._engine()
        company = (
            request.env["res.company"].browse(int(company_id))
            if company_id
            else request.env.company
        )
        # FIX: same guard as get_data — don't trust the client-supplied
        # company_id, and cap how many comparison periods one request
        # can trigger.
        if company_id and int(company_id) not in request.env.user.company_ids.ids:
            raise AccessError(_("You do not have access to this company's data."))
        comparison_periods = self._cap_comparison_periods(comparison_periods)
        # FIX: same analytic_account_ids cap as get_data() — protects the
        # tax report query domain from an unbounded IN-clause too.
        analytic_account_ids = self._cap_analytic_accounts(analytic_account_ids)
        result = engine.get_tax_report(
            date_from=date_from,
            date_to=date_to,
            company_id=company.id,
            target_move=target_move,
            analytic_account_ids=analytic_account_ids,
        )

        if comparison_periods:
            comp_periods = []
            for period in comparison_periods:
                p_from = period.get("date_from")
                p_to = period.get("date_to")
                if not p_from or not p_to:
                    continue
                comp = engine.get_tax_report(
                    date_from=p_from,
                    date_to=p_to,
                    company_id=company.id,
                    target_move=target_move,
                    analytic_account_ids=analytic_account_ids,
                )
                comp_periods.append({
                    "label": period.get("label", ""),
                    "date_to": p_to,
                    "date_from": p_from,
                    "lines": comp["lines"],
                })
            if comp_periods:
                result["lines"] = engine.merge_tax_comparison_lines(
                    result["lines"], comp_periods
                )
                result["comparison_columns"] = [
                    {"label": p["label"], "date_to": p["date_to"]}
                    for p in comp_periods
                ]

        # FIX: pass both date_from and date_to for proper period-scoped check
        result["has_unposted"] = engine.has_unposted_entries(
            date_from=date_from,
            date_to=date_to,
            company_id=company.id,
        )
        return result

    # ------------------------------------------------------------------
    # /fs_enterprise/export_tax_pdf
    # ------------------------------------------------------------------
    @http.route("/fs_enterprise/export_tax_pdf", type="json", auth="user")
    def export_tax_pdf(
        self,
        date_from=None,
        date_to=None,
        company_id=None,
        target_move="posted",
        comparison_periods=None,
        analytic_account_ids=None,
        **kwargs,
    ):
        self._check_account_group()
        data = self.get_tax_report(
            date_from=date_from,
            date_to=date_to,
            company_id=company_id,
            target_move=target_move,
            comparison_periods=comparison_periods,
            analytic_account_ids=analytic_account_ids,
        )
        lines = data.get("lines", [])
        company_name = data.get("company_name", "")
        currency_symbol = data.get("currency_symbol", "")
        currency_digits = data.get("currency_digits", 2)
        comparison_columns = data.get("comparison_columns", [])

        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import mm
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        except ImportError:
            return {"error": "reportlab is not installed on this server."}

        output = io.BytesIO()
        doc = SimpleDocTemplate(
            output, pagesize=landscape(A4),
            leftMargin=15 * mm, rightMargin=15 * mm,
            topMargin=15 * mm, bottomMargin=15 * mm,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "TaxTitle", parent=styles["Normal"],
            fontSize=13, fontName="Helvetica-Bold", spaceAfter=3,
        )
        sub_style = ParagraphStyle(
            "TaxSub", parent=styles["Normal"],
            fontSize=10, fontName="Helvetica", spaceAfter=2,
        )
        period_style = ParagraphStyle(
            "TaxPeriod", parent=styles["Normal"],
            fontSize=9, fontName="Helvetica", spaceAfter=8,
        )

        C_HEADER_BG = colors.HexColor("#e8e8e8")
        C_SECTION_BG = colors.HexColor("#f0f0f0")
        C_SUBTOTAL_BG = colors.HexColor("#f0f0f0")
        C_TOTAL_BG = colors.HexColor("#e0e0e0")
        C_BORDER = colors.HexColor("#cccccc")
        C_COMP_BG = colors.HexColor("#f5f5dc")

        page_w = landscape(A4)[0] - 30 * mm
        col_num = 12 * mm
        col_amt = 42 * mm
        col_vat = 42 * mm
        num_comp = len(comparison_columns)
        if num_comp:
            col_comp = 38 * mm
            total_fixed = col_num + col_amt + col_vat
            remaining = page_w - total_fixed
            needed = num_comp * 2 * col_comp
            if remaining <= 0 or (remaining / (num_comp * 2)) < 12 * mm:
                col_amt = max(18 * mm, remaining / (num_comp * 2 + 2) * 2)
                col_vat = col_amt
                col_num = max(8 * mm, remaining / (num_comp * 2 + 2))
                remaining = page_w - col_num - col_amt - col_vat
            col_comp = remaining / (num_comp * 2)
            col_comp = max(12 * mm, col_comp)
            total_comp_width = num_comp * 2 * col_comp
            col_name = page_w - col_num - col_amt - col_vat - total_comp_width
            if col_name < 15 * mm:
                scale = (page_w - 15 * mm) / (page_w - col_name + 15 * mm) if (page_w - col_name + 15 * mm) > 0 else 0.5
                col_num = max(8 * mm, col_num * scale)
                col_amt = max(18 * mm, col_amt * scale)
                col_vat = max(18 * mm, col_vat * scale)
                col_comp = max(12 * mm, col_comp * scale)
                total_comp_width = num_comp * 2 * col_comp
                col_name = page_w - col_num - col_amt - col_vat - total_comp_width
            col_name = max(15 * mm, col_name)
        else:
            col_name = page_w - col_num - col_amt - col_vat

        col_widths = [col_num, col_name, col_amt, col_vat]
        if num_comp:
            for _ in range(num_comp):
                col_widths.extend([col_comp, col_comp])

        cell_n = ParagraphStyle("TaxCellN", parent=styles["Normal"], fontSize=7, fontName="Helvetica")
        cell_b = ParagraphStyle("TaxCellB", parent=styles["Normal"], fontSize=7, fontName="Helvetica-Bold")
        cell_r = ParagraphStyle("TaxCellR", parent=styles["Normal"], fontSize=7, fontName="Helvetica", alignment=2)
        cell_rb = ParagraphStyle("TaxCellRB", parent=styles["Normal"], fontSize=7, fontName="Helvetica-Bold", alignment=2)
        cell_center = ParagraphStyle("TaxCellC", parent=styles["Normal"], fontSize=7, fontName="Helvetica-Bold", alignment=1)

        def p(text, style=cell_n):
            return Paragraph(str(text) if text is not None else "", style)

        def fmt(v):
            if v is None:
                return ""
            try:
                # dynamic decimals per currency
                return format(float(v), f",.{currency_digits}f")
            except Exception:
                return str(v)

        num_cols = 4 + num_comp * 2

        current_label = ""
        if date_to:
            try:
                parts = str(date_to).split("-")
                y = parts[0]
                m = int(parts[1]) if len(parts) > 1 else 0
                d = int(parts[2]) if len(parts) > 2 else 0
                if m == 1 and d <= 1:
                    current_label = y
                elif m in (1, 4, 7, 10) and d <= 1:
                    q = (m - 1) // 3 + 1
                    current_label = f"Q{q} {y}"
                else:
                    from datetime import date as _date
                    month_names = [
                        "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
                    ]
                    current_label = f"{month_names[m]} {y}"
            except Exception:
                current_label = str(date_to)

        if num_comp:
            row_period = [
                p("", cell_b), p("", cell_b),
                p(current_label, cell_center),
            ]
            for col in comparison_columns:
                row_period.append(p(col.get("label", ""), cell_center))
                row_period.append(p("", cell_b))
            table_data = [row_period]

            row_sub = [
                p("#", cell_b), p("Description", cell_b),
                p(f"Amount ({currency_symbol})", cell_b),
                p(f"VAT Amount ({currency_symbol})", cell_b),
            ]
            for _ in range(num_comp):
                row_sub.append(p(f"Amount ({currency_symbol})", cell_b))
                row_sub.append(p(f"VAT Amount ({currency_symbol})", cell_b))
            table_data.append(row_sub)
        else:
            header_row = [
                p("#", cell_b), p("Description", cell_b),
                p(f"Amount ({currency_symbol})", cell_b),
                p(f"VAT Amount ({currency_symbol})", cell_b),
            ]
            table_data = [header_row]

        row_meta = []

        data_start_row = 2 if num_comp else 1
        for line in lines:
            ri = data_start_row + len(row_meta)
            if line.get("section_header"):
                row_cells = [p(""), p(line.get("name", ""), cell_b), p(""), p("")]
                for _ in range(num_comp):
                    row_cells.extend([p(""), p("")])
                table_data.append(row_cells)
                row_meta.append((ri, "section"))
                continue

            sk = line.get("style", "data")
            is_bold = sk in ("total", "subtotal", "summary")
            lbl = cell_b if is_bold else cell_n
            num_lbl = cell_rb if is_bold else cell_r

            num = line.get("number", "")
            base = fmt(line.get("base_amount")) if line.get("show_base") else ""
            vat = fmt(line.get("vat_amount")) if line.get("show_vat") else ""

            row_cells = [
                p(f"{num}." if num else "", lbl),
                p(line.get("name", ""), lbl),
                p(base, num_lbl),
                p(vat, num_lbl),
            ]

            comp_balances = line.get("comparison_balances") or []
            for ci in range(num_comp):
                cb = comp_balances[ci] if ci < len(comp_balances) else {}
                comp_base = fmt(cb.get("base_amount")) if line.get("show_base") else ""
                comp_vat = fmt(cb.get("vat_amount")) if line.get("show_vat") else ""
                row_cells.append(p(comp_base, num_lbl))
                row_cells.append(p(comp_vat, num_lbl))

            table_data.append(row_cells)
            row_meta.append((ri, sk))

        ts_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), C_HEADER_BG),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.3, C_BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]

        if num_comp:
            ts_cmds += [
                ("BACKGROUND", (0, 1), (-1, 1), C_HEADER_BG),
                ("SPAN", (0, 0), (0, 1)),
                ("SPAN", (1, 0), (1, 1)),
                ("SPAN", (2, 0), (3, 0)),
            ]
            for ci in range(num_comp):
                col_start = 4 + ci * 2
                col_end = col_start + 1
                ts_cmds.append(("SPAN", (col_start, 0), (col_end, 0)))

        for ri, sk in row_meta:
            if sk == "section":
                ts_cmds += [
                    ("BACKGROUND", (0, ri), (-1, ri), C_SECTION_BG),
                    ("SPAN", (0, ri), (-1, ri)),
                    ("FONTNAME", (0, ri), (-1, ri), "Helvetica-Bold"),
                ]
            elif sk == "total":
                ts_cmds += [
                    ("BACKGROUND", (0, ri), (-1, ri), C_TOTAL_BG),
                    ("FONTNAME", (0, ri), (-1, ri), "Helvetica-Bold"),
                    ("LINEABOVE", (0, ri), (-1, ri), 1, colors.black),
                ]
            elif sk == "subtotal":
                ts_cmds += [
                    ("BACKGROUND", (0, ri), (-1, ri), C_SUBTOTAL_BG),
                    ("FONTNAME", (0, ri), (-1, ri), "Helvetica-Bold"),
                ]

        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle(ts_cmds))

        story = [
            Paragraph(company_name, title_style),
            Paragraph("Tax Return (VAT Report)", sub_style),
            Paragraph(f"{date_from or ''} to {date_to or ''}", period_style),
            table,
        ]
        doc.build(story)

        label = f"Tax_Report_{date_to or 'report'}"
        return {
            "file_content": base64.b64encode(output.getvalue()).decode("utf-8"),
            "file_name": f"{label}.pdf",
        }

    # ------------------------------------------------------------------
    # /fs_enterprise/export_tax_xlsx
    # ------------------------------------------------------------------
    @http.route("/fs_enterprise/export_tax_xlsx", type="json", auth="user")
    def export_tax_xlsx(
        self,
        date_from=None,
        date_to=None,
        company_id=None,
        target_move="posted",
        comparison_periods=None,
        analytic_account_ids=None,
        **kwargs,
    ):
        self._check_account_group()
        data = self.get_tax_report(
            date_from=date_from,
            date_to=date_to,
            company_id=company_id,
            target_move=target_move,
            comparison_periods=comparison_periods,
            analytic_account_ids=analytic_account_ids,
        )
        lines = data.get("lines", [])
        company_name = data.get("company_name", "")
        currency_symbol = data.get("currency_symbol", "")
        currency_digits = data.get("currency_digits", 2)
        comparison_columns = data.get("comparison_columns", [])
        num_comp = len(comparison_columns)

        try:
            import xlsxwriter
        except ImportError:
            return {"error": "xlsxwriter is not installed on this server."}

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("Tax Report")

        bold = workbook.add_format({"bold": True})
        border_c = "#cccccc"
        num_fmt = "#,##0." + ("0" * currency_digits) if currency_digits > 0 else "#,##0"
        header_fmt = workbook.add_format({
            "bold": True, "bg_color": "#e8e8e8", "font_color": "#000000",
            "border": 1, "border_color": border_c, "align": "center",
        })
        section_fmt = workbook.add_format({
            "bold": True, "bg_color": "#f0f0f0", "font_color": "#000000",
            "border": 1, "border_color": border_c,
        })
        subtotal_num = workbook.add_format({
            "bold": True, "bg_color": "#f0f0f0", "border": 1,
            "border_color": border_c, "num_format": num_fmt,
        })
        subtotal_lbl = workbook.add_format({
            "bold": True, "bg_color": "#f0f0f0", "border": 1, "border_color": border_c,
        })
        total_num = workbook.add_format({
            "bold": True, "bg_color": "#e0e0e0", "font_color": "#000000",
            "border": 1, "border_color": border_c, "top": 2, "num_format": num_fmt,
        })
        total_lbl = workbook.add_format({
            "bold": True, "bg_color": "#e0e0e0", "font_color": "#000000",
            "border": 1, "border_color": border_c, "top": 2,
        })
        summary_num = workbook.add_format({
            "bold": True, "bg_color": "#ffffff", "border": 1,
            "border_color": border_c, "num_format": num_fmt,
        })
        summary_lbl = workbook.add_format({
            "bold": True, "bg_color": "#ffffff", "border": 1, "border_color": border_c,
        })
        data_num = workbook.add_format({
            "border": 1, "border_color": border_c, "num_format": num_fmt,
        })
        data_lbl = workbook.add_format({"border": 1, "border_color": border_c})

        last_col = 3 + num_comp * 2
        sheet.set_column(0, 0, 8)
        sheet.set_column(1, 1, 55)
        sheet.set_column(2, last_col, 18)

        sheet.merge_range(0, 0, 0, last_col, company_name, bold)
        sheet.merge_range(1, 0, 1, last_col, "Tax Return (VAT Report)", bold)
        sheet.merge_range(2, 0, 2, last_col, f"{date_from or ''} to {date_to or ''}", data_lbl)
        sheet.write(3, 0, "")

        row = 4
        sheet.write(row, 0, "#", header_fmt)
        sheet.write(row, 1, "Description", header_fmt)
        sheet.write(row, 2, f"Amount ({currency_symbol})", header_fmt)
        sheet.write(row, 3, f"VAT Amount ({currency_symbol})", header_fmt)
        col_idx = 4
        for col in comparison_columns:
            sheet.write(row, col_idx, col.get("label", ""), header_fmt)
            sheet.write(row, col_idx + 1, f"VAT ({currency_symbol})", header_fmt)
            col_idx += 2
        row += 1

        for line in lines:
            if line.get("section_header"):
                if num_comp:
                    sheet.merge_range(row, 0, row, last_col, line.get("name", ""), section_fmt)
                else:
                    sheet.merge_range(row, 0, row, 3, line.get("name", ""), section_fmt)
                row += 1
                continue

            sk = line.get("style", "data")
            if sk == "total":
                lf, nf = total_lbl, total_num
            elif sk == "subtotal":
                lf, nf = subtotal_lbl, subtotal_num
            elif sk == "summary":
                lf, nf = summary_lbl, summary_num
            else:
                lf, nf = data_lbl, data_num

            num = line.get("number", "")
            base = line.get("base_amount") if line.get("show_base") else None
            vat = line.get("vat_amount") if line.get("show_vat") else None

            sheet.write(row, 0, f"{num}." if num else "", lf)
            sheet.write(row, 1, line.get("name", ""), lf)
            if base is not None:
                sheet.write_number(row, 2, float(base), nf)
            else:
                sheet.write_blank(row, 2, None, lf)
            if vat is not None:
                sheet.write_number(row, 3, float(vat), nf)
            else:
                sheet.write_blank(row, 3, None, lf)

            comp_balances = line.get("comparison_balances") or []
            col_idx = 4
            for ci in range(num_comp):
                cb = comp_balances[ci] if ci < len(comp_balances) else {}
                comp_base = cb.get("base_amount")
                comp_vat = cb.get("vat_amount")
                if line.get("show_base") and comp_base is not None:
                    sheet.write_number(row, col_idx, float(comp_base), nf)
                else:
                    sheet.write_blank(row, col_idx, None, lf)
                if line.get("show_vat") and comp_vat is not None:
                    sheet.write_number(row, col_idx + 1, float(comp_vat), nf)
                else:
                    sheet.write_blank(row, col_idx + 1, None, lf)
                col_idx += 2

            row += 1

        workbook.close()
        label = f"Tax_Report_{date_to or 'report'}"
        return {
            "file_content": base64.b64encode(output.getvalue()).decode("utf-8"),
            "file_name": f"{label}.xlsx",
        }

    # ------------------------------------------------------------------
    # /fs_enterprise/get_analytic_accounts
    # FIX: filter by current company (and global accounts with no company)
    # ------------------------------------------------------------------
    @http.route("/fs_enterprise/get_analytic_accounts", type="json", auth="user")
    def get_analytic_accounts(self, company_id=None, **kwargs):
        self._check_account_group()
        company = (
            request.env["res.company"].browse(int(company_id))
            if company_id
            else request.env.company
        )
        # FIX: restrict to company-specific + global analytic accounts
        # FIX (multi-company): evaluate record rules for the REPORT company,
        # not only the user's active company.
        accounts = request.env["account.analytic.account"].with_context(
            allowed_company_ids=[company.id]
        ).search_read(
            [("company_id", "in", [False, company.id])],
            ["id", "name"],
            order="name",
        )
        return accounts

    # ------------------------------------------------------------------
    # /fs_enterprise/export_excel
    # ------------------------------------------------------------------
    @http.route("/fs_enterprise/export_excel", type="json", auth="user")
    def export_excel(
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
        analytic_account_ids=None,
        with_debit_credit=False,
        include_unassigned=False,
        **kwargs,
    ):
        self._check_account_group()
        data = self.get_data(
            report_type=report_type,
            date_from=date_from,
            date_to=date_to,
            company_id=company_id,
            target_move=target_move,
            comparison_mode=comparison_mode,
            comparison_date_from=comparison_date_from,
            comparison_date_to=comparison_date_to,
            comparison_periods=comparison_periods,
            analytic_account_ids=analytic_account_ids,
            with_debit_credit=with_debit_credit,
            include_unassigned=include_unassigned,
        )
        lines = data.get("lines", [])
        comparison_cols = data.get("comparison_columns", [])
        company_name = data.get("company_name", "")
        currency_symbol = data.get("currency_symbol", "")
        currency_digits = data.get("currency_digits", 2)
        report_title = "Balance Sheet" if report_type == "bs" else "Profit and Loss"

        show_dc = bool(with_debit_credit) and not comparison_cols

        try:
            import xlsxwriter
        except ImportError:
            return {"error": "xlsxwriter is not installed on this server."}

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("Report")

        bold = workbook.add_format({"bold": True})
        title_fmt = workbook.add_format({"bold": True, "font_size": 12})
        header_fmt = workbook.add_format({
            "bold": True, "bg_color": "#1e3a5f", "font_color": "#ffffff",
            "border": 1, "align": "center",
        })

        # FIX: dynamic decimal format per currency (BHD/KWD 3 decimals)
        num_format_str = "#,##0." + ("0" * currency_digits) if currency_digits > 0 else "#,##0"

        def make_formats(bg=None, is_bold=False):
            base = {"border": 1}
            if bg:
                base["bg_color"] = bg
            if is_bold:
                base["bold"] = True
            lbl_fmts, num_fmts = {}, {}
            for level in range(6):
                lbl_fmts[level] = workbook.add_format(dict(base, indent=level))
                num_fmts[level] = workbook.add_format(
                    dict(base, indent=level, num_format=num_format_str, align="right")
                )
            return lbl_fmts, num_fmts

        header_lbl, header_num = make_formats(bg="#eeeeee", is_bold=True)
        subtotal_lbl, subtotal_num = make_formats(is_bold=True)
        data_lbl, data_num = make_formats()

        analytic_cols = data.get("analytic_columns", [])

        col_headers = ["Account"]
        if analytic_cols:
            for ac in analytic_cols:
                col_headers.append(ac.get("name", ""))
        elif show_dc:
            col_headers += ["Debit", "Credit", "Balance"]
        else:
            col_headers.append(f"Balance ({currency_symbol})" if currency_symbol else "Balance")
            for c in comparison_cols:
                col_headers.append(c.get("label", ""))
        num_cols = len(col_headers) - 1

        sheet.set_column(0, 0, 45)
        for col_idx in range(1, num_cols + 1):
            sheet.set_column(col_idx, col_idx, 18)

        sheet.merge_range(0, 0, 0, num_cols, company_name, title_fmt)
        sheet.merge_range(1, 0, 1, num_cols, report_title, title_fmt)
        date_lbl_val = (
            f"As of {date_to or ''}"
            if report_type == "bs"
            else f"From {date_from or ''} to {date_to or ''}"
        )
        sheet.merge_range(2, 0, 2, num_cols, date_lbl_val, bold)
        sheet.write(3, 0, "")

        row = 4
        for c_idx, h_text in enumerate(col_headers):
            sheet.write(row, c_idx, h_text, header_fmt)
        row += 1

        def get_comp_val(line, col_label):
            cb_list = line.get("comparison_balances", [])
            for cb in cb_list:
                if cb.get("label") == col_label:
                    return cb.get("balance", 0.0)
            return line.get("comparison_balance", 0.0)

        # FIX (recursion): iterative DFS to avoid Python recursion limit / stack overflow on deep/wide charts
        # Pre-order traversal: parent written before children, same as original recursion
        stack = list(reversed(lines)) if lines else []
        while stack:
            line = stack.pop()
            sk = line.get("style", "data")
            level = min(line.get("level", 0), 5)

            if sk == "header":
                lf, nf = header_lbl[level], header_num[level]
            elif sk in ("subtotal", "total", "summary"):
                lf, nf = subtotal_lbl[level], subtotal_num[level]
            else:
                lf, nf = data_lbl[level], data_num[level]

            sheet.write(row, 0, line.get("name") or "", lf)

            if analytic_cols:
                ab_map = line.get("analytic_balances") or {}
                for a_idx, acol in enumerate(analytic_cols):
                    a_key = acol.get("id")
                    val = ab_map.get(a_key, ab_map.get(str(a_key), 0.0))
                    sheet.write_number(row, a_idx + 1, float(val or 0.0), nf)
            elif show_dc:
                sheet.write_number(row, 1, float(line.get("debit") or 0.0), nf)
                sheet.write_number(row, 2, float(line.get("credit") or 0.0), nf)
                sheet.write_number(row, 3, float(line.get("balance") or 0.0), nf)
            else:
                sheet.write_number(row, 1, float(line.get("balance") or 0.0), nf)
                for c_idx, col in enumerate(comparison_cols):
                    val = get_comp_val(line, col.get("label"))
                    sheet.write_number(row, c_idx + 2, float(val or 0.0), nf)

            row += 1
            children = line.get("children") or []
            if children:
                # push in reverse to keep original order when popping
                for child in reversed(children):
                    stack.append(child)

        workbook.close()
        label = f"{report_title.replace(' ', '_')}_{date_to or 'report'}"
        return {
            "file_content": base64.b64encode(output.getvalue()).decode("utf-8"),
            "file_name": f"{label}.xlsx",
        }