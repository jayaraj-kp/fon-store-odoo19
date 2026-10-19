# Copyright 2024 Custom Development
# License: LGPL-3.0 or later

import base64
import datetime
import io
import json
import logging
import math

import xlsxwriter
from markupsafe import escape
from werkzeug.wrappers import Response

from odoo import _, fields, http
from odoo.exceptions import AccessError, UserError
from odoo.http import content_disposition, request
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)

SCREEN_MAX_LINES = 5000
PDF_MAX_LINES = 1000        # wkhtmltopdf crashes / times out above ~1000 rows
EXCEL_MAX_LINES = 100000


def _e(value):
    """HTML-escape any value (never put raw data into the PDF HTML)."""
    return str(escape("" if value is None else value))


class OcaDailyReportsController(http.Controller):
    """JSON controller for Enterprise-style Daily Reports."""

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _engine(self):
        return request.env["daily.reports.engine"]

    def _company(self, company_id=None):
        if company_id:
            company = request.env["res.company"].browse(int(company_id))
            if company not in request.env.user.company_ids:
                raise AccessError(_("You are not allowed to access this company."))
            return company
        return request.env.company

    def _limit(self, key, default):
        """Limits can be changed in System Parameters (daily_reports.<key>)."""
        value = request.env["ir.config_parameter"].sudo().get_param(
            "daily_reports.%s" % key, default
        )
        try:
            return max(1, int(value))
        except (TypeError, ValueError):
            return default

    def _fmt_date(self, d):
        if not d:
            return ""
        try:
            parts = str(d).split("-")
            return "%s/%s/%s" % (parts[2], parts[1], parts[0])
        except Exception:
            return str(d)

    def _safe_filename_date(self, d):
        if not d:
            return "report"
        try:
            return fields.Date.to_date(d).isoformat()
        except Exception:
            return "report"

    def _fmt_num(self, val):
        if val is None:
            return ""
        try:
            return "{:,.2f}".format(float(val))
        except Exception:
            return str(val)

    def _collect(self, limit, **params):
        company = self._company(params.get("company_id"))
        data = self._engine().get_report_data(
            report_type=params.get("report_type", "cash_book"),
            date_from=params.get("date_from"),
            date_to=params.get("date_to"),
            company_id=company.id,
            journal_ids=params.get("journal_ids"),
            target_move=params.get("target_move", "posted"),
            partner_ids=params.get("partner_ids"),
            analytic_account_ids=params.get("analytic_account_ids"),
            limit=limit,
        )
        return company, data

    def _ensure_complete(self, data, kind):
        """Printed / exported files must never be partial."""
        if data.get("truncated"):
            raise UserError(_(
                "This report has %(total)s lines, which is more than the %(kind)s "
                "limit (%(limit)s). Please narrow the date range or filters%(hint)s.",
                total=data.get("total_lines"),
                kind=kind,
                limit=data.get("max_lines"),
                hint=_(", or use Excel export") if kind == "PDF" else "",
            ))

    # ------------------------------------------------------------------
    # PDF pieces
    # ------------------------------------------------------------------
    def _render_footer_html(self, company):
        """Footer comes from the company record (no hard-coded data):
        bank accounts of the company partner + company 'Report Footer' text."""
        banks = company.partner_id.bank_ids
        cells = []
        for bank in banks:
            cells.append(
                '<td><div class="fl-co">%s</div><div class="fl-badge">%s</div>'
                '<div class="fl-line"><span class="fl-label">Account / IBAN</span> '
                '<span class="fl-value">%s</span></div></td>'
                % (
                    _e(bank.acc_holder_name or company.name),
                    _e(bank.bank_id.name),
                    _e(bank.acc_number),
                )
            )
        rows = []
        for i in range(0, len(cells), 2):
            pair = cells[i:i + 2]
            if len(pair) == 1:
                pair.append("<td></td>")
            rows.append("<tr>%s</tr>" % "".join(pair))
        banks_html = ""
        if rows:
            banks_html = (
                '<div class="fl-section-label">Bank Accounts</div>'
                '<table class="fl-banks">%s</table>' % "".join(rows)
            )

        extra_lines = [
            ln.strip()
            for ln in html2plaintext(company.report_footer or "").splitlines()
            if ln.strip()
        ]
        extra_html = ""
        if extra_lines:
            extra_html = '<div class="fl-extra">%s</div>' % "<br/>".join(
                _e(ln) for ln in extra_lines
            )

        template = r"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>
  html, body { margin:0; padding:0; font-family:Arial,sans-serif; }
  #dr-bank-footer { font-size:11px; line-height:1.25; color:#222; padding:6px 18px 4px; }
  table { width:100%; border-collapse:collapse; table-layout:fixed; margin:0; }
  td { border:none; vertical-align:top; padding:0 14px 4px 0; }
  .fl-section-label { font-size:9.5px; font-weight:700; letter-spacing:.8px; color:#111;
      text-transform:uppercase; margin:0 0 3px; border-bottom:1px solid #ccc; }
  .fl-co { font-size:11.5px; color:#111; }
  .fl-badge { font-size:10px; text-transform:uppercase; color:#333; margin-bottom:2px; }
  .fl-line { font-size:10.5px; }
  .fl-label { color:#777; }
  .fl-extra { font-size:9.5px; color:#444; margin-top:4px; border-top:1px solid #999; padding-top:3px; }
</style></head>
<body onload="drFooterInit()">
<div id="dr-bank-footer">__BANKS____EXTRA__</div>
<div id="dr-page-num" style="text-align:center;font-size:9px;color:#999;padding:5px 0 2px;"></div>
<div style="border-top:2px solid #8b0000;"></div>
<script>
  function drFooterInit() {
    var qs = (document.location.search || '').replace(/^\?/, '');
    var params = {};
    qs.split('&').forEach(function(pair) {
      var kv = pair.split('=');
      if (kv[0]) { params[kv[0]] = decodeURIComponent(kv[1] || ''); }
    });
    var page = parseInt(params.page, 10), topage = parseInt(params.topage, 10);
    var bankEl = document.getElementById('dr-bank-footer');
    var pageEl = document.getElementById('dr-page-num');
    if (bankEl && page && topage && page !== topage) { bankEl.style.display = 'none'; }
    if (pageEl && page && topage) { pageEl.textContent = 'Page ' + page + ' of ' + topage; }
  }
</script></body></html>"""
        html = template.replace("__BANKS__", banks_html).replace("__EXTRA__", extra_html)
        margin_bottom = min(70, 22 + 9 * math.ceil(len(cells) / 2) + 4 * len(extra_lines))
        return html, margin_bottom

    def _get_default_header_html(self, company, report_title):
        logo_html = ""
        logo = company.logo
        if logo:
            logo_b64 = logo.decode() if isinstance(logo, bytes) else logo
            logo_html = (
                '<img src="data:image/png;base64,%s" style="max-width:110px;'
                'max-height:80px;object-fit:contain;display:block;margin:0 0 0 auto;"/>'
                % logo_b64
            )
        return (
            '<table style="width:100%%; border-collapse:collapse; margin:0 0 6px; border:none;">'
            '<tr><td style="vertical-align:middle; text-align:left; border:none;">'
            '<div style="font-size:16px; font-weight:bold; color:#111;">%(name)s</div>'
            '<div style="font-size:10.5px; color:#777; margin-top:3px;">VAT Number: '
            '<span style="font-weight:bold; color:#111;">%(vat)s</span></div>'
            '<div style="font-size:19px; font-weight:bold; color:#111; margin-top:7px;">%(title)s</div>'
            '</td><td style="width:150px; vertical-align:middle; padding:0 0 0 16px; '
            'text-align:right; border:none;">%(logo)s</td></tr></table>'
            '<div style="border-bottom:2px solid #111; margin:0 0 8px;"></div>'
            % {
                "name": _e(company.name),
                "vat": _e(company.vat),
                "title": _e(report_title),
                "logo": logo_html,
            }
        )

    def _render_lines_html(self, lines, report_title, currency_symbol, show_balance=True):
        thead = (
            "<tr><th>Entry / Particulars</th><th>Partner</th><th>Journal</th>"
            "<th>Account</th><th>Date</th><th>Ref</th>"
            "<th class='right'>Debit</th><th class='right'>Credit</th>"
            "<th class='right'>Balance</th></tr>"
        )
        symbol = _e(currency_symbol)

        def balance_cell(value):
            if not show_balance or value is None:
                return "<td></td>"
            return "<td class='right'>%s %s</td>" % (_e(self._fmt_num(value)), symbol)

        def render_line(line, depth=0):
            lt = line.get("line_type", "")
            indent = "&nbsp;" * (depth * 4)
            name = _e(report_title if lt == "total" else line.get("name"))
            css = (
                "total-row" if lt == "total"
                else "group-row" if lt in ("group", "opening")
                else "sub-row"
            )
            if lt in ("group", "opening"):
                cells = "<td>%s%s</td>%s" % (indent, name, "<td></td>" * 8)
            else:
                cells = (
                    "<td>%s%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td>"
                    "<td class='right'>%s</td><td class='right'>%s</td>%s"
                ) % (
                    indent, name,
                    _e(line.get("partner_name")),
                    _e(line.get("journal")),
                    _e(line.get("account")),
                    _e(self._fmt_date(line.get("invoice_date"))),
                    _e(line.get("ref")),
                    _e(self._fmt_num(line.get("debit"))),
                    _e(self._fmt_num(line.get("credit"))),
                    balance_cell(line.get("balance")),
                )
            html = "<tr class='%s'>%s</tr>\n" % (css, cells)
            for child in line.get("children") or []:
                html += render_line(child, depth + 1)
            return html

        total_line = None
        body = lines
        if lines and lines[0].get("line_type") == "total":
            total_line, body = lines[0], lines[1:]

        tbody = ""
        if total_line:
            tbody += "<tr class='total-row'><td>%s</td>%s</tr>\n" % (
                _e(report_title), "<td></td>" * 8
            )
        for line in body:
            tbody += render_line(line)
        if total_line:
            tbody += render_line(total_line)
        return "<table><thead>%s</thead><tbody>%s</tbody></table>" % (thead, tbody)

    # ------------------------------------------------------------------
    # JSON routes
    # ------------------------------------------------------------------
    @http.route("/dr/init", type="json", auth="user")
    def get_init_data(self, company_id=None):
        env = request.env
        company = self._company(company_id)
        companies = env["res.company"].search_read(
            [("id", "in", env.user.company_ids.ids)], ["id", "name"], order="name"
        )
        journals = env["account.journal"].search_read(
            [("company_id", "=", company.id)],
            ["id", "name", "code", "type"], order="name",
        )
        today = datetime.date.today()
        date_from = today.replace(month=1, day=1)
        date_to = today.replace(month=12, day=31)
        try:  # use the company's real fiscal year when available
            fy = company.compute_fiscalyear_dates(today)
            date_from, date_to = fy["date_from"], fy["date_to"]
        except Exception:
            pass
        return {
            "companies": companies,
            "company_id": company.id,
            "company_name": company.name,
            "currency_name": company.currency_id.name,
            "currency_symbol": company.currency_id.symbol,
            "journals": journals,
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "fiscal_year": today.year,
        }

    @http.route("/dr/search_partners", type="json", auth="user")
    def search_partners(self, term=None, **kwargs):
        term = (term or "").strip()[:100]
        if not term:
            return []
        domain = [
            ("name", "ilike", term),
            "|",
            ("company_id", "=", False),
            ("company_id", "in", request.env.companies.ids),
        ]
        return request.env["res.partner"].search_read(
            domain, ["id", "name"], limit=20, order="name"
        )

    @http.route("/dr/search_analytics", type="json", auth="user")
    def search_analytics(self, term=None, **kwargs):
        domain = [
            "|",
            ("company_id", "=", False),
            ("company_id", "in", request.env.companies.ids),
        ]
        term = (term or "").strip()[:100]
        if term:
            domain.append(("name", "ilike", term))
        return request.env["account.analytic.account"].search_read(
            domain, ["id", "name"], limit=50, order="name"
        )

    @http.route("/dr/get_data", type="json", auth="user")
    def get_data(self, report_type="cash_book", date_from=None, date_to=None,
                 company_id=None, journal_ids=None, target_move="posted",
                 partner_ids=None, analytic_account_ids=None, **kwargs):
        company, result = self._collect(
            self._limit("screen_max_lines", SCREEN_MAX_LINES),
            report_type=report_type, date_from=date_from, date_to=date_to,
            company_id=company_id, journal_ids=journal_ids,
            target_move=target_move, partner_ids=partner_ids,
            analytic_account_ids=analytic_account_ids,
        )
        result["has_unposted"] = self._engine().has_unposted_entries(
            date_from=date_from, date_to=date_to, company_id=company.id
        )
        return result

    @http.route("/dr/export_pdf", type="json", auth="user")
    def export_pdf(self, report_type="cash_book", date_from=None, date_to=None,
                   company_id=None, journal_ids=None, target_move="posted",
                   partner_ids=None, analytic_account_ids=None, **kwargs):
        company, data = self._collect(
            self._limit("pdf_max_lines", PDF_MAX_LINES),
            report_type=report_type, date_from=date_from, date_to=date_to,
            company_id=company_id, journal_ids=journal_ids,
            target_move=target_move, partner_ids=partner_ids,
            analytic_account_ids=analytic_account_ids,
        )
        self._ensure_complete(data, "PDF")
        report_title = data.get("report_title", "Daily Report")

        header_html = self._get_default_header_html(company, report_title)
        lines_html = self._render_lines_html(
            data.get("lines", []), report_title,
            data.get("currency_symbol", ""), data.get("show_balance", True),
        )
        footer_html, margin_bottom = self._render_footer_html(company)

        period = ""
        if date_from and date_to:
            period = "%s - %s" % (self._fmt_date(date_from), self._fmt_date(date_to))
        period = _e(period)
        if not data.get("integrity_ok", True):
            period += (
                "<br/><span style='color:#b00020;font-weight:bold;'>WARNING: %s</span>"
                % _e(" | ".join(data.get("integrity_messages", [])))
            )

        page = r"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>
  body { font-family: Arial, sans-serif; font-size: 12px; margin: 0; padding: 0; }
  .page-wrapper { box-sizing: border-box; padding: 0 12px; }
  table { width: 100%; border-collapse: collapse; margin-top: 8px; }
  th, td { border: 1px solid #ccc; padding: 4px 6px; font-size: 11px; }
  th { background: #f0f0f0; text-align: left; font-weight: bold; }
  .group-row { background: #e8e8e8; font-weight: bold; }
  .total-row { background: #d0d0d0; font-weight: bold; }
  .right { text-align: right; }
  .sub-row { color: #333; }
  .period { margin: 6px 0; font-size: 12px; color: #555; text-align:center;
            padding:3px; background:#f5f5f5; border:1px solid #ddd; }
</style></head>
<body><div class="page-wrapper">
__HEADER__
<div class="period">__PERIOD__</div>
__LINES__
</div></body></html>"""
        html = (
            page.replace("__HEADER__", header_html)
            .replace("__PERIOD__", period)
            .replace("__LINES__", lines_html)
        )

        pdf_content = request.env["ir.actions.report"]._run_wkhtmltopdf(
            [html],
            landscape=False,
            footer=footer_html,
            specific_paperformat_args={
                "data-report-margin-top": 3,
                "data-report-margin-bottom": margin_bottom,
                "data-report-margin-left": 10,
                "data-report-margin-right": 10,
                "data-report-header-spacing": 0,
            },
        )
        prefix = report_title.replace(" ", "_")
        return {
            "file_content": base64.b64encode(pdf_content).decode("utf-8"),
            "file_name": "%s_%s.pdf" % (prefix, self._safe_filename_date(date_to)),
        }

    @http.route("/dr/export_excel", type="json", auth="user")
    def export_excel(self, report_type="cash_book", date_from=None, date_to=None,
                     company_id=None, journal_ids=None, target_move="posted",
                     partner_ids=None, analytic_account_ids=None, **kwargs):
        company, data = self._collect(
            self._limit("excel_max_lines", EXCEL_MAX_LINES),
            report_type=report_type, date_from=date_from, date_to=date_to,
            company_id=company_id, journal_ids=journal_ids,
            target_move=target_move, partner_ids=partner_ids,
            analytic_account_ids=analytic_account_ids,
        )
        self._ensure_complete(data, "Excel")
        report_title = data.get("report_title", "Daily Report")
        content = self._generate_excel_content(
            data, date_from=date_from, date_to=date_to, target_move=target_move
        )
        prefix = report_title.replace(" ", "_")
        return {
            "file_content": base64.b64encode(content).decode("utf-8"),
            "file_name": "%s_%s.xlsx" % (prefix, self._safe_filename_date(date_to)),
        }

    @http.route("/dr/export_excel_stream", type="http", auth="user", methods=["GET"], csrf=False)
    def export_excel_stream(self, report_type="cash_book", date_from=None, date_to=None,
                            company_id=None, journal_ids=None, target_move="posted",
                            partner_ids=None, analytic_account_ids=None, **kwargs):
        """Stream the Excel file directly as an HTTP download.

        Advantages over the old JSON route:
        * The workbook is built with ``constant_memory=True`` so xlsxwriter
          flushes rows to a temp file — RAM stays flat even for 100k rows.
        * The final bytes are sent straight to the browser as a file
          attachment: no base64 inflation (+33 %), no JSON body overhead.
        * Odoo's worker memory / response-size limits no longer apply.

        GET params are plain strings (same names as the JSON route so the JS
        can be migrated with a one-line change).
        """
        # journal_ids / partner_ids / analytic_account_ids arrive as
        # comma-separated strings from a query-string GET request.
        def _split_ids(raw):
            if not raw:
                return None
            return [v.strip() for v in str(raw).split(",") if v.strip()]

        try:
            company, data = self._collect(
                self._limit("excel_max_lines", EXCEL_MAX_LINES),
                report_type=report_type,
                date_from=date_from,
                date_to=date_to,
                company_id=company_id,
                journal_ids=_split_ids(journal_ids),
                target_move=target_move,
                partner_ids=_split_ids(partner_ids),
                analytic_account_ids=_split_ids(analytic_account_ids),
            )
            self._ensure_complete(data, "Excel")
        except (UserError, AccessError) as exc:
            # Return the real error message as plain text so the browser's
            # fetch() can read it directly.  Without this, Odoo's middleware
            # renders an HTML error page and JSON.parse() fails in JS,
            # showing only a generic "server error 400" instead of the
            # actual reason (e.g. "report has 1,50,000 lines …").
            return Response(
                str(exc),
                status=400,
                content_type="text/plain; charset=utf-8",
            )
        report_title = data.get("report_title", "Daily Report")
        content = self._generate_excel_content(
            data, date_from=date_from, date_to=date_to, target_move=target_move
        )
        prefix = report_title.replace(" ", "_")
        file_name = "%s_%s.xlsx" % (prefix, self._safe_filename_date(date_to))
        return Response(
            content,
            status=200,
            headers={
                "Content-Type": (
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ),
                "Content-Disposition": content_disposition(file_name),
                "Content-Length": str(len(content)),
                "Cache-Control": "no-cache",
            },
        )

    # ------------------------------------------------------------------
    # Excel
    # ------------------------------------------------------------------
    def _generate_excel_content(self, data, date_from=None, date_to=None,
                                target_move="posted"):
        output = io.BytesIO()
        # constant_memory: rows are flushed to disk, safe for 100k+ rows
        wb = xlsxwriter.Workbook(output, {"constant_memory": True})
        title = data.get("report_title", "Daily Report")
        ws = wb.add_worksheet(title[:31])
        show_balance = data.get("show_balance", True)
        font = "Segoe UI"

        def mk(**kw):
            base = {"font_name": font, "valign": "vcenter"}
            base.update(kw)
            return wb.add_format(base)

        num = "#,##0.00"
        f_title = mk(bold=True, font_size=14, font_color="#111827")
        f_sub = mk(bold=True, font_size=11, font_color="#374151")
        f_meta = mk(font_size=9, font_color="#4B5563")
        f_warn = mk(font_size=9, bold=True, font_color="#B00020")
        th = {"bold": True, "font_size": 10, "bg_color": "#714B67",
              "font_color": "#FFFFFF", "border": 1, "border_color": "#58364F"}
        th_l, th_c, th_r = (mk(**th, align=a) for a in ("left", "center", "right"))
        gb = {"bold": True, "font_size": 9, "bg_color": "#E5E7EB",
              "border": 1, "border_color": "#D1D5DB"}
        g_l, g_c = mk(**gb, align="left"), mk(**gb, align="center")
        g_n = mk(**gb, num_format=num, align="right")
        ob = {"italic": True, "font_size": 9, "bg_color": "#F3F4F6",
              "font_color": "#4B5563", "border": 1, "border_color": "#E5E7EB"}
        o_l, o_n = mk(**ob, align="left"), mk(**ob, num_format=num, align="right")
        lb = {"font_size": 9, "border": 1, "border_color": "#E5E7EB"}
        l_l, l_c = mk(**lb, align="left"), mk(**lb, align="center")
        l_n = mk(**lb, num_format=num, align="right")
        tb = {"bold": True, "font_size": 10, "bg_color": "#D1D5DB",
              "top": 1, "bottom": 6, "border_color": "#9CA3AF"}
        t_l, t_n = mk(**tb, align="left"), mk(**tb, num_format=num, align="right")

        G = [g_l, g_l, g_l, g_l, g_c, g_l, g_n, g_n, g_n]
        O = [o_l] * 8 + [o_n]
        L = [l_l, l_l, l_l, l_l, l_c, l_l, l_n, l_n, l_n]
        T = [t_l] * 6 + [t_n] * 3

        for col, width in enumerate((32, 26, 12, 14, 14, 20, 16, 16, 18)):
            ws.set_column(col, col, width)

        def put(row, values, fmts):
            for col, (val, fm) in enumerate(zip(values, fmts)):
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    ws.write_number(row, col, float(val), fm)
                else:
                    ws.write_string(row, col, "" if val is None else str(val), fm)

        def bal(value):
            return "" if (not show_balance or value is None) else value

        company_name = data.get("company_name") or ""
        ws.write_string(0, 0, company_name, f_title)
        ws.write_string(1, 0, title, f_sub)
        if date_from and date_to:
            period = "Period: %s to %s" % (
                self._fmt_date(date_from), self._fmt_date(date_to))
        else:
            period = ""
        target_label = "Posted Entries" if target_move == "posted" else "Include Unposted"
        ws.write_string(2, 0, "%s   |   Target Moves: %s   |   Currency: %s (%s)" % (
            period, target_label, data.get("currency_name") or "",
            data.get("currency_symbol") or ""), f_meta)
        if not data.get("integrity_ok", True):
            ws.write_string(3, 0, "WARNING: " + " | ".join(
                data.get("integrity_messages", [])), f_warn)

        headers = ["Entry / Particulars", "Partner", "Journal", "Account", "Date",
                   "Ref", "Debit", "Credit", "Balance"]
        header_fmts = [th_l, th_l, th_l, th_l, th_c, th_l, th_r, th_r, th_r]
        put(4, headers, header_fmts)
        ws.freeze_panes(5, 0)

        lines = data.get("lines", [])
        total = lines[0] if lines and lines[0].get("line_type") == "total" else None
        body = lines[1:] if total else lines
        row = 5

        if total:
            put(row, [title] + [""] * 8, G)
            row += 1

        for line in body:
            lt = line.get("line_type")
            if lt == "opening":
                put(row, [line.get("name") or "Opening Balance", "", "", "", "", "",
                          line.get("debit") or 0.0, line.get("credit") or 0.0,
                          bal(line.get("balance"))], G)
                row += 1
            elif lt == "group":
                put(row, [line.get("name") or "", "", line.get("journal") or "", "",
                          "", "", line.get("debit") or 0.0, line.get("credit") or 0.0,
                          bal(line.get("balance"))], G)
                row += 1
                if line.get("opening_balance") is not None:
                    put(row, ["    Opening Balance", "", "", "", "", "", "", "",
                              line.get("opening_balance")], O)
                    row += 1
                for child in line.get("children") or []:
                    put(row, [
                        "    " + str(child.get("name") or ""),
                        child.get("partner_name") or "",
                        child.get("journal") or "",
                        child.get("account") or "",
                        self._fmt_date(child.get("invoice_date")),
                        child.get("ref") or "",
                        child.get("debit") or 0.0,
                        child.get("credit") or 0.0,
                        bal(child.get("balance")),
                    ], L)
                    row += 1

        if total:
            put(row, [title, "", "", "", "", "", total.get("debit") or 0.0,
                      total.get("credit") or 0.0, bal(total.get("balance"))], T)

        wb.close()
        output.seek(0)
        return output.read()