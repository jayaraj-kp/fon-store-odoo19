

# Copyright 2024 Custom Development
# License: LGPL-3.0 or later

import base64
import datetime
import io
import logging

import xlsxwriter

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PartnerLedgerController(http.Controller):
    """JSON controller for the Enterprise-style Partner Ledger OWL view."""

    def _engine(self):
        return request.env["partner.ledger.engine"]

    def _get_default_header_html(self, company, report_title):
        """Build a professional report header: company name / VAT / report
        title left-aligned on the LEFT, company logo on the RIGHT, and a
        bold bottom rule underneath. Plain black/grey, no accent colors.
        """
        logo_html = ""
        logo = company.logo
        if logo:
            logo_b64 = logo.decode() if isinstance(logo, bytes) else logo
            logo_html = (
                '<img src="data:image/png;base64,{src}" '
                'style="max-width:110px;max-height:80px;object-fit:contain;'
                'display:block;margin:0 0 0 auto;"/>'
            ).format(src=logo_b64)

        vat = company.vat or ""

        return """
<table style="width:100%; border-collapse:collapse; margin:0 0 6px;">
  <tr>
    <td style="vertical-align:middle; text-align:left;">
      <div style="font-size:16px; font-weight:bold; color:#111; letter-spacing:0.3px;">{name}</div>
      <div style="font-size:10.5px; color:#777; margin-top:3px;">
        VAT Number: <span style="font-weight:bold; color:#111;">{vat}</span>
      </div>
      <div style="font-size:19px; font-weight:bold; color:#111; margin-top:7px; letter-spacing:0.5px;">{title}</div>
    </td>
    <td style="width:150px; vertical-align:middle; padding:0 0 0 16px; text-align:right;">
      {logo}
    </td>
  </tr>
</table>
<div style="border-bottom:2px solid #111; margin:0 0 8px;"></div>
""".format(
            logo=logo_html,
            name=company.name or "",
            vat=vat,
            title=report_title,
        )

    def _render_footer_html(self):
        """Return a STANDALONE HTML document to hand to wkhtmltopdf as its
        real --footer-html.

        Unlike the old approach (bank block glued into normal document flow
        and absolutely-positioned against a wrapper whose height simply
        grows with the content), this is wkhtmltopdf's native footer
        mechanism: wkhtmltopdf loads this document separately for EVERY
        physical page, reserves the paperformat's bottom margin for it, and
        appends its own real page/topage query params (page=N&topage=M) to
        this document's URL when it does.

        The inline script below reads those params and hides the bank
        block on every page except the last one, so it only ever shows up
        once, flush against the bottom of the final physical page -
        regardless of how many pages the report spans."""
        return """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
  html, body { margin:0; padding:0; font-family:Arial,sans-serif; }
  #pl_footer_outer {
    box-sizing: border-box;
  }
  #pl_bank_footer {
    font-size: 11px;
    line-height: 1.25;
    color: #222;
    padding: 6px 18px 4px;
    box-sizing: border-box;
  }
  #pl_bank_footer table { width:100%; border-collapse:collapse; table-layout:fixed; margin:0; }
  #pl_bank_footer td { border:none; vertical-align:top; }

  .fl-section-label {
    font-size: 9.5px;
    font-weight: 700;
    letter-spacing: 0.8px;
    color: #111;
    text-transform: uppercase;
    margin: 0 0 3px;
    padding-bottom: 1px;
    border-bottom: 1px solid #ccc;
  }

  /* ---- Bank accounts ---- */
  .fl-banks td { width:50%; padding:0 14px 3px 0; }
  .fl-banks td + td { padding:0 0 3px 16px; border-left:1px solid #ddd; }
  .fl-co     { font-size:11.5px; font-weight:normal; color:#111; margin-bottom:1px; }
  .fl-badge  {
    font-size: 10px;
    font-weight: normal;
    letter-spacing: 0.3px;
    text-transform: uppercase;
    color: #333;
    white-space: nowrap;
    margin-bottom: 2px;
  }
  .fl-row { width:100%; }
  .fl-row td { border:none; padding:0; font-size:10.5px; }
  .fl-label { width:105px; color:#777; }
  .fl-value { font-weight:normal; color:#111; }

  /* ---- Branches ---- */
  .fl-branches-wrap { margin-top:4px; }
  .fl-branches td {
    width:33.33%;
    padding:3px 12px 1px 0;
    border-top:1px solid #999;
  }
  .fl-branches td + td { padding:3px 12px; border-left:1px solid #eee; }
  .fl-branches td:last-child { padding:3px 0 1px 12px; }
  .fl-branch-name { font-size:10.5px; font-weight:normal; color:#111; margin-bottom:1px; }
  .fl-branch-info { font-size:9.5px; color:#444; margin-bottom:0; }
  .fl-branch-info b { color:#666; font-weight:normal; }
</style>
</head>
<body onload="plFooterInit()">
<div id="pl_footer_outer">
<div id="pl_bank_footer">

  <div class="fl-section-label">Bank Accounts</div>
  <table class="fl-banks">
    <tr>
      <td>
        <div class="fl-co">Sameer Sharaf Al Otaibi Trading Company</div>
        <div class="fl-badge">Alrajhi Bank</div>
        <table class="fl-row">
          <tr><td class="fl-label">Account Number</td><td class="fl-value">123000010006080143917</td></tr>
          <tr><td class="fl-label">IBAN</td><td class="fl-value">SA7880000123608010143917</td></tr>
        </table>
      </td>
      <td>
        <div class="fl-co">Sameer Sharaf Alateebi Company Commercial</div>
        <div class="fl-badge">SNB \u2013 Saudi National Bank</div>
        <table class="fl-row">
          <tr><td class="fl-label">Account Number</td><td class="fl-value">13200000678707</td></tr>
          <tr><td class="fl-label">IBAN</td><td class="fl-value">SA2110000013200000678707</td></tr>
        </table>
      </td>
    </tr>
  </table>

  <div class="fl-branches-wrap">
    <div class="fl-section-label">Branch Locations</div>
    <table class="fl-branches">
      <tr>
        <td>
          <div class="fl-branch-name">Jeddah Al Fayha Branch</div>
          <div class="fl-branch-info">7655 Al Fayha Dist., Jeddah 22244-3108, Saudi Arabia</div>
          <div class="fl-branch-info"><b>Tel:</b> +966 571 313 243</div>
          <div class="fl-branch-info"><b>Email:</b> ssaoe.jeddah@gmail.com</div>
        </td>
        <td>
          <div class="fl-branch-name">Jeddah Baladiya Branch</div>
          <div class="fl-branch-info">Sookul Anwar, Al Baladeah, Aziziyah, Jeddah 31303, Saudi Arabia</div>
          <div class="fl-branch-info"><b>Tel:</b> +966 536 122 833</div>
          <div class="fl-branch-info"><b>Email:</b> ssaoe.jeddah@gmail.com</div>
        </td>
        <td>
          <div class="fl-branch-name">Dammam Branch</div>
          <div class="fl-branch-info">8515 Qutaibah bin Muslim St., Al Souq, Dammam 4525-32242, Saudi Arabia</div>
          <div class="fl-branch-info"><b>Tel:</b> +966 535 081 008</div>
          <div class="fl-branch-info"><b>Email:</b> ssaoe.jeddah@gmail.com</div>
        </td>
      </tr>
    </table>
  </div>

</div>

<div id="pl_page_num" style="text-align:center;font-size:9px;color:#999;padding:5px 0 2px;"></div>

<div style="border-top:2px solid #8b0000;"></div>

</div>
<script>
  function plFooterInit() {
    var qs = (document.location.search || '').replace(/^\\?/, '');
    var params = {};
    qs.split('&').forEach(function(pair) {
      var kv = pair.split('=');
      if (kv[0]) { params[kv[0]] = decodeURIComponent(kv[1] || ''); }
    });
    var page   = parseInt(params.page,   10);
    var topage = parseInt(params.topage, 10);
    var bankEl = document.getElementById('pl_bank_footer');
    var pageEl = document.getElementById('pl_page_num');
    if (bankEl && page && topage && page !== topage) {
      bankEl.style.display = 'none';
    }
    if (pageEl && page && topage) {
      pageEl.textContent = 'Page ' + page + ' of ' + topage;
    }
  }
</script>
</body>
</html>"""

    # ------------------------------------------------------------------
    # /pl/init
    # ------------------------------------------------------------------
    @http.route("/pl/init", type="json", auth="user")
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
        date_to = today.replace(month=12, day=31).isoformat()

        return {
            "companies": companies,
            "company_id": company.id,
            "company_name": company.name,
            "currency_name": company.currency_id.name,
            "currency_symbol": company.currency_id.symbol,
            "date_from": date_from,
            "date_to": date_to,
            "fiscal_year": today.year,
        }

    # ------------------------------------------------------------------
    # /pl/get_data
    # ------------------------------------------------------------------
    @http.route("/pl/get_data", type="json", auth="user")
    def get_data(
        self,
        date_from,
        date_to,
        company_id=None,
        account_types=None,
        partner_ids=None,
        tag_ids=None,
        target_move="posted",
        **kwargs,
    ):
        engine = self._engine()
        company = (
            request.env["res.company"].browse(int(company_id))
            if company_id
            else request.env.company
        )

        result = engine.get_partner_ledger(
            date_from=date_from,
            date_to=date_to,
            company_id=company.id,
            account_types=account_types,
            partner_ids=partner_ids,
            tag_ids=tag_ids,
            target_move=target_move,
        )
        result["has_unposted"] = engine.has_unposted_entries(
            date_from=date_from, date_to=date_to, company_id=company.id
        )
        return result

    # ------------------------------------------------------------------
    # /pl/search_partners
    # ------------------------------------------------------------------
    @http.route("/pl/search_partners", type="json", auth="user")
    def search_partners(self, term="", limit=8):
        partners = request.env["res.partner"].search_read(
            [("name", "ilike", term)] if term else [],
            ["id", "name", "customer_rank", "supplier_rank"],
            limit=limit,
            order="name",
        )
        return partners

    # ------------------------------------------------------------------
    # /pl/search_tags
    # ------------------------------------------------------------------
    @http.route("/pl/search_tags", type="json", auth="user")
    def search_tags(self, term="", limit=8):
        tags = request.env["res.partner.category"].search_read(
            [("name", "ilike", term)] if term else [],
            ["id", "name"],
            limit=limit,
            order="name",
        )
        return tags

    def _get_page_geometry(self):
        """Return (page_height_mm, margin_top_mm, margin_bottom_mm) matching
        what wkhtmltopdf will ACTUALLY use for this PDF.

        Margins are fixed here (10mm top / 5mm bottom) because we force
        those same values via specific_paperformat_args in export_pdf,
        overriding whatever margins the paperformat itself defines.

        Page HEIGHT, however, is NOT overridden by this code — wkhtmltopdf
        takes it straight from the company's configured report.paperformat
        record (Settings > Technical > Report Paperformats: either a named
        size like A4/US Letter, or a custom page_height). So we read that
        same record here to compute the exact usable content height,
        instead of hardcoding a guess (e.g. assuming A4's 297mm when the
        company might actually be on US Letter, or a custom size). If the
        admin changes the paperformat in the UI, this automatically
        follows it.
        """
        # margin_bottom is now the reserved wkhtmltopdf --footer area (see
        # export_pdf: footer=... is a real --footer-html document). It must
        # be tall enough to fit the two bank/branch tables + email line
        # (~70-90px), which 5mm was not, hence the previous clipped/glued
        # look. 44mm gives comfortable room for both the bank-accounts and
        # branch-locations sections; bump further if still tight.
        margin_top, margin_bottom = 3, 44
        # Always read geometry from this module's own dedicated Portrait A4
        # paperformat (defined in report_templates.xml) rather than the
        # company's globally configured default paperformat. The company
        # default may be set to Landscape (or a custom landscape-shaped size)
        # for other reports, which would otherwise leak into this export -
        # this report must always be Portrait regardless of that setting.
        paperformat = request.env.ref(
            "partner_ledger_enterprise_view.paperformat_partner_ledger",
            raise_if_not_found=False,
        )
        # wkhtmltopdf's built-in --page-size names, height in mm.
        format_heights = {
            "a4": 297.0,
            "us_letter": 279.4,
            "us_legal": 355.6,
            "tabloid": 431.8,
            "a3": 420.0,
            "a5": 210.0,
            "b4": 353.0,
            "b5": 250.0,
        }
        if paperformat and paperformat.page_height:
            # Custom paperformat: page_height is already an explicit mm value.
            page_height = paperformat.page_height
        elif paperformat and paperformat.format:
            page_height = format_heights.get(paperformat.format.lower(), 297.0)
        else:
            page_height = 297.0  # A4 fallback if no paperformat is configured at all
        return page_height, margin_top, margin_bottom

    # ------------------------------------------------------------------
    # /pl/export_pdf
    # ------------------------------------------------------------------
    @http.route("/pl/export_pdf", type="json", auth="user")
    def export_pdf(
        self,
        date_from,
        date_to,
        company_id=None,
        account_types=None,
        partner_ids=None,
        tag_ids=None,
        target_move="posted",
        report_view="partner_ledger",
        show_footer=False,
        **kwargs,
    ):
        # Resolve partner names for display in the PDF header
        partner_names = ""
        if partner_ids:
            partners = request.env["res.partner"].browse(partner_ids)
            partner_names = ", ".join(p.name for p in partners if p.name)
        data = self.get_data(
            date_from=date_from,
            date_to=date_to,
            company_id=company_id,
            account_types=account_types,
            partner_ids=partner_ids,
            tag_ids=tag_ids,
            target_move=target_move,
        )
        if report_view == "customer_statement":
            report_title = "Statement of Account"
        else:
            # Determine title from actual partner data: for single-partner
            # PDFs use that partner's account types; for multi-partner use "Ledger".
            report_title = "Ledger"
            all_lines = data.get("lines", [])
            partner_groups = [
                ln for ln in all_lines if ln.get("line_type") == "partner"
            ]
            if len(partner_groups) == 1:
                children = partner_groups[0].get("children") or []
                report_title = self._partner_type_label(children)

        # Real page geometry, read from the company's configured paper
        # format rather than assumed — see _get_page_geometry() above.
        page_height_mm, margin_top_mm, margin_bottom_mm = self._get_page_geometry()

        # ------------------------------------------------------------------
        # Build the full PDF HTML directly in Python. Header is the plain
        # default-style block (logo + name + country + VAT + report title)
        # built from res.company, not the old full-width custom banner.
        # ------------------------------------------------------------------
        header_html = self._get_default_header_html(request.env.company, report_title)

        lines_html = self._render_lines_html(
            data.get("lines", []),
            report_view,
            report_title,
            data.get("currency_symbol", ""),
        )

        # Only include the bank/branch footer when:
        #   - show_footer toggle is ON, AND
        #   - report is NOT "Supplier Ledger"
        is_supplier_ledger = report_title == "Supplier Ledger"
        use_footer = show_footer and not is_supplier_ledger
        footer_html = self._render_footer_html() if use_footer else None
        if not use_footer:
            margin_bottom_mm = 5
        usable_height_mm = round(page_height_mm - margin_top_mm - margin_bottom_mm, 1)

        html = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
  body {{ font-family: Arial, sans-serif; font-size: 12px; margin: 0; padding: 0; }}
  /* wkhtmltopdf's rendering engine (old WebKit/Qt) does not reliably
     support display:flex — flex properties are silently ignored, which is
     why an earlier flex-based approach had no effect. position:absolute /
     relative is CSS2.1 and renders correctly.

     .page-wrapper's min-height ({usable_height}mm) is computed in Python
     from the company's ACTUAL configured report.paperformat (page size +
     margins), not a hardcoded guess — see _get_page_geometry(). This
     keeps the CSS in sync with wherever wkhtmltopdf really breaks pages,
     so changing the paper format in Settings > Technical > Report
     Paperformats is picked up automatically. */
  .page-wrapper {{
    box-sizing: border-box;
    padding: 0px 20px 20px;
  }}
  .report-header {{ width: 100%; margin-bottom: 10px; }}
  .report-header img {{ width: 100%; max-height: 110px; object-fit: contain; display: block; }}
  table.data-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
  table.data-table th, table.data-table td {{ border: 1px solid #ccc; padding: 4px 6px; font-size: 11px; }}
  table.data-table th {{ background: #f0f0f0; text-align: left; }}
  .bold {{ font-weight: bold; }}
  .group-row {{ background: #e8e8e8; font-weight: bold; }}
  .total-row {{ background: #d0d0d0; font-weight: bold; }}
  .right {{ text-align: right; }}
  .sub-row {{ color: #333; }}
  .period {{ width: 100%; box-sizing: border-box; margin: 0 0 10px; padding: 6px 0;
             background: #f0f0f0; font-size: 11px; color: #333; text-align: center; }}
  .partner-section {{ margin-bottom: 16px; }}
  .partner-section-title {{ font-size: 13px; font-weight: bold; color: #222;
                            margin: 0 0 4px; padding: 4px 8px;
                            background: #e0e0e0; border-left: 3px solid #555; }}
</style>
</head>
<body>
<div class="page-wrapper">
  <div class="report-content">
    {header}
    {partner_line}
    <div class="period">{date_from} - {date_to}</div>
    {lines}
  </div>
</div>
</body>
</html>""".format(
            header=header_html,
            date_from=self._fmt_date(date_from),
            date_to=self._fmt_date(date_to),
            partner_line=(
                f'<div style="text-align:center; font-size:15px; font-weight:bold; '
                f'margin:0 0 6px; color:#111; letter-spacing:0.3px;">'
                f'{partner_names}</div>'
            ) if partner_names else "",
            lines=lines_html,
            usable_height=usable_height_mm,
        )

        # Use Odoo's wkhtmltopdf wrapper to convert HTML → PDF.
        # Margins are forced to margin_top_mm / margin_bottom_mm (10/5),
        # overriding whatever the paperformat defines for those. Page
        # HEIGHT is intentionally left alone here so it comes from the
        # company's actual configured report.paperformat — and that same
        # real height is what _get_page_geometry() read above to compute
        # usable_height_mm for the CSS, so the two stay in sync no matter
        # what paper size is configured in Settings > Technical > Report
        # Paperformats. The footer is absolutely positioned against that
        # page-wrapper, so on short reports it sits flush at the true
        # bottom of the (real) page; on long reports it simply follows
        # the last row once content overflows past the first page.
        # Bind the report call to the dedicated Portrait A4 paperformat (see
        # _get_page_geometry above) instead of letting it fall back to
        # env.company.paperformat_id, which guarantees this export is always
        # Portrait no matter what the company's own default is set to.
        portrait_paperformat = request.env.ref(
            "partner_ledger_enterprise_view.paperformat_partner_ledger",
            raise_if_not_found=False,
        )
        report_obj = request.env["ir.actions.report"]
        if portrait_paperformat:
            report_obj = report_obj.new({"paperformat_id": portrait_paperformat.id})
        pdf_content = report_obj._run_wkhtmltopdf(
            [html],
            landscape=False,
            footer=footer_html or "",
            specific_paperformat_args={
                "data-report-margin-top": margin_top_mm,
                "data-report-margin-bottom": margin_bottom_mm,
                "data-report-margin-left": 8,
                "data-report-margin-right": 8,
                "data-report-header-spacing": 0,
            },
        )

        file_prefix = report_title.replace(" ", "_")
        return {
            "file_content": base64.b64encode(pdf_content).decode("utf-8"),
            "file_name": f"{file_prefix}_{date_to or 'report'}.pdf",
        }

    # ------------------------------------------------------------------
    # /pl/export_excel
    # ------------------------------------------------------------------
    @http.route("/pl/export_excel", type="json", auth="user")
    def export_excel(
        self,
        date_from,
        date_to,
        company_id=None,
        account_types=None,
        partner_ids=None,
        tag_ids=None,
        target_move="posted",
        report_view="partner_ledger",
        **kwargs,
    ):
        """Export the current report data to a .xlsx workbook (one flat
        table matching the PDF columns, with a header + total row)."""
        data = self.get_data(
            date_from=date_from,
            date_to=date_to,
            company_id=company_id,
            account_types=account_types,
            partner_ids=partner_ids,
            tag_ids=tag_ids,
            target_move=target_move,
        )
        lines = data.get("lines", [])
        is_stmt = report_view == "customer_statement"

        # Flatten the nested structure the same way the PDF does: partner
        # rows act as section headers, their children are the detail rows,
        # and the first element may be the grand-total row.
        total_line = None
        body_lines = lines
        if lines and lines[0].get("line_type") == "total":
            total_line = lines[0]
            body_lines = lines[1:]

        rows = []
        for line in body_lines:
            rows.append(line)
            rows.extend(line.get("children") or [])
        if total_line:
            rows.append(total_line)

        if is_stmt:
            headers = [
                "Entry", "Invoice Date", "Due Date", "Reference",
                "Amount", "Balance",
            ]
        else:
            headers = [
                "Account", "Invoice Date", "Due Date", "Reference",
                "Entry", "Debit", "Credit", "Balance",
            ]

        def cell_values(line):
            name = line.get("name") or ""
            if line.get("line_type") == "total":
                name = "Total"
            bal = line.get("balance") or 0.0
            if is_stmt:
                amt = (line.get("debit") or 0.0) - (line.get("credit") or 0.0)
                return [
                    name,
                    self._fmt_date(line.get("invoice_date")),
                    self._fmt_date(line.get("due_date")),
                    line.get("reference") or "",
                    round(amt, 2),
                    round(bal, 2),
                ]
            return [
                line.get("account") or (name if line.get("line_type") == "total" else ""),
                self._fmt_date(line.get("invoice_date")),
                self._fmt_date(line.get("due_date")),
                line.get("reference") or "",
                "" if line.get("line_type") == "total" else name,
                round(line.get("debit") or 0.0, 2),
                round(line.get("credit") or 0.0, 2),
                round(bal, 2),
            ]

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        worksheet = workbook.add_worksheet("Report")

        header_fmt = workbook.add_format(
            {"bold": True, "bg_color": "#D9D9D9", "border": 1, "valign": "vcenter"}
        )
        group_fmt = workbook.add_format(
            {"bold": True, "bg_color": "#F2F2F2", "border": 1}
        )
        total_fmt = workbook.add_format(
            {"bold": True, "bg_color": "#E0E0E0", "border": 1, "top": 2}
        )
        cell_fmt = workbook.add_format({"border": 1})
        num_fmt = workbook.add_format({"border": 1, "num_format": "#,##0.00"})

        for col, title in enumerate(headers):
            worksheet.write(0, col, title, header_fmt)

        row_idx = 1
        for line in rows:
            lt = line.get("line_type", "")
            fmt = total_fmt if lt == "total" else group_fmt if lt == "partner" else cell_fmt
            values = cell_values(line)
            for col, value in enumerate(values):
                is_num = isinstance(value, (int, float))
                worksheet.write(
                    row_idx, col, value, num_fmt if is_num else fmt
                )
            row_idx += 1

        width = {0: 28, 1: 13, 2: 13, 3: 22, 4: 28, 5: 14, 6: 14, 7: 14}
        for col, w in width.items():
            if col < len(headers):
                worksheet.set_column(col, col, w)
        worksheet.freeze_panes(1, 0)
        worksheet.autofilter(0, 0, max(0, row_idx - 1), len(headers) - 1)

        workbook.close()
        file_content = output.getvalue()

        file_prefix = (
            "Statement_of_Account" if is_stmt else "Partner_Ledger"
        )
        return {
            "file_content": base64.b64encode(file_content).decode("utf-8"),
            "file_name": f"{file_prefix}_{date_to or 'report'}.xlsx",
        }

    # ------------------------------------------------------------------
    # HTML rendering helpers
    # ------------------------------------------------------------------
    def _fmt_date(self, d):
        """Convert YYYY-MM-DD to DD/MM/YYYY."""
        if not d:
            return ""
        try:
            parts = d.split("-")
            return f"{parts[2]}/{parts[1]}/{parts[0]}"
        except Exception:
            return d or ""

    def _fmt_num(self, val):
        if val is None:
            return ""
        try:
            return f"{float(val):,.2f}"
        except Exception:
            return str(val)

    @staticmethod
    def _partner_type_label(children):
        """Determine a partner's ledger type from their account lines."""
        has_receivable = any(
            c.get("account_type") == "asset_receivable"
            for c in children
        )
        has_payable = any(
            c.get("account_type") == "liability_payable"
            for c in children
        )
        if has_receivable and not has_payable:
            return "Customer Ledger"
        if has_payable and not has_receivable:
            return "Supplier Ledger"
        return "Ledger"

    def _render_lines_html(self, lines, report_view, report_title, currency_symbol):
        """Render report lines as HTML. Each partner gets its own table
        with a section header and a per-partner Total row."""
        is_stmt = report_view == "customer_statement"

        if is_stmt:
            thead = (
                "<tr>"
                "<th>Entry</th>"
                "<th>Invoice Date</th>"
                "<th>Due Date</th>"
                "<th>Reference</th>"
                "<th class='right'>Amount</th>"
                "<th class='right'>Balance</th>"
                "</tr>"
            )
        else:
            thead = (
                "<tr>"
                "<th>Account</th>"
                "<th>Invoice Date</th>"
                "<th>Due Date</th>"
                "<th>Reference</th>"
                "<th>Entry</th>"
                "<th class='right'>Debit</th>"
                "<th class='right'>Credit</th>"
                "<th class='right'>Balance</th>"
                "</tr>"
            )

        def render_detail(line):
            lt = line.get("line_type", "")
            name = line.get("name", "")
            bal = line.get("balance") or 0.0
            bal_str = f"{self._fmt_num(bal)} {currency_symbol}".strip()
            if is_stmt:
                amt = (line.get("debit") or 0.0) - (line.get("credit") or 0.0)
                cells = (
                    f"<td>{name}</td>"
                    f"<td>{self._fmt_date(line.get('invoice_date'))}</td>"
                    f"<td>{self._fmt_date(line.get('due_date'))}</td>"
                    f"<td>{line.get('reference') or ''}</td>"
                    f"<td class='right'>{self._fmt_num(amt)}</td>"
                    f"<td class='right'>{bal_str}</td>"
                )
            else:
                cells = (
                    f"<td>{line.get('account') or ''}</td>"
                    f"<td>{self._fmt_date(line.get('invoice_date'))}</td>"
                    f"<td>{self._fmt_date(line.get('due_date'))}</td>"
                    f"<td>{line.get('reference') or ''}</td>"
                    f"<td>{name}</td>"
                    f"<td class='right'>{self._fmt_num(line.get('debit'))}</td>"
                    f"<td class='right'>{self._fmt_num(line.get('credit'))}</td>"
                    f"<td class='right'>{bal_str}</td>"
                )
            return f"<tr class='sub-row'>{cells}</tr>\n"

        def render_partner_total(debit, credit, balance):
            bal_str = f"{self._fmt_num(balance)} {currency_symbol}".strip()
            if is_stmt:
                amt = debit - credit
                cells = (
                    "<td></td><td></td><td></td><td></td>"
                    "<td><b>Total</b></td>"
                    f"<td class='right'><b>{self._fmt_num(amt)}</b></td>"
                    f"<td class='right'><b>{bal_str}</b></td>"
                )
            else:
                cells = (
                    "<td></td><td></td><td></td><td></td>"
                    "<td><b>Total</b></td>"
                    f"<td class='right'><b>{self._fmt_num(debit)}</b></td>"
                    f"<td class='right'><b>{self._fmt_num(credit)}</b></td>"
                    f"<td class='right'><b>{bal_str}</b></td>"
                )
            return f"<tr class='total-row'>{cells}</tr>\n"

        # Group lines by partner (skip the grand total line)
        body_lines = lines
        if lines and lines[0].get("line_type") == "total":
            body_lines = lines[1:]

        partner_groups = []
        for line in body_lines:
            if line.get("line_type") == "partner":
                partner_groups.append(line)

        html_parts = []
        single_partner = len(partner_groups) == 1
        for group in partner_groups:
            pname = group.get("name", "")
            children = group.get("children") or []
            ptype = self._partner_type_label(children) if not is_stmt else ""

            if pname and not single_partner:
                html_parts.append(
                    f"<div class='partner-section'>"
                    f"<h3 class='partner-section-title'>{pname}"
                    f"<span style='font-weight:normal;font-size:11px;color:#555;margin-left:8px;'>"
                    f"({ptype})</span></h3>"
                )
            html_parts.append(
                f"<table class='data-table'><thead>{thead}</thead><tbody>"
            )
            for child in children:
                html_parts.append(render_detail(child))

            # Per-partner subtotal row
            total_debit = sum(c.get("debit") or 0.0 for c in children)
            total_credit = sum(c.get("credit") or 0.0 for c in children)
            total_balance = children[-1].get("balance", 0.0) if children else 0.0
            html_parts.append(render_partner_total(total_debit, total_credit, total_balance))

            html_parts.append("</tbody></table>")
            if pname and not single_partner:
                html_parts.append("</div>")

        return "\n".join(html_parts)

    # ==================================================================
    # AGED RECEIVABLE
    # ==================================================================
    def _aged_engine(self):
        return request.env["aged.receivable.engine"]

    # ------------------------------------------------------------------
    # /pl/aged/init
    # ------------------------------------------------------------------
    @http.route("/pl/aged/init", type="json", auth="user")
    def aged_init_data(self, company_id=None):
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
        return {
            "companies": companies,
            "company_id": company.id,
            "company_name": company.name,
            "currency_name": company.currency_id.name,
            "currency_symbol": company.currency_id.symbol,
            "date_as_of": today.isoformat(),
        }

    # ------------------------------------------------------------------
    # /pl/aged/get_data
    # ------------------------------------------------------------------
    @http.route("/pl/aged/get_data", type="json", auth="user")
    def aged_get_data(
        self,
        date_as_of,
        company_id=None,
        account_types=None,
        partner_ids=None,
        tag_ids=None,
        target_move="posted",
        days_interval=30,
        based_on="due_date",
        **kwargs,
    ):
        engine = self._aged_engine()
        company = (
            request.env["res.company"].browse(int(company_id))
            if company_id
            else request.env.company
        )
        result = engine.get_aged_receivable(
            date_as_of=date_as_of,
            company_id=company.id,
            account_types=account_types,
            partner_ids=partner_ids,
            tag_ids=tag_ids,
            target_move=target_move,
            days_interval=int(days_interval),
            based_on=based_on,
        )
        acct_types = account_types or ["receivable"]
        total_name = "Aged Payable" if acct_types == ["payable"] else "Aged Receivable"
        for line in result.get("lines", []):
            if line.get("line_type") == "total":
                line["name"] = total_name
        result["has_unposted"] = engine.has_unposted_entries(
            date_as_of=date_as_of, company_id=company.id
        )
        return result

    # ------------------------------------------------------------------
    # /pl/aged/export_pdf
    # ------------------------------------------------------------------
    @http.route("/pl/aged/export_pdf", type="json", auth="user")
    def aged_export_pdf(
        self,
        date_as_of,
        company_id=None,
        account_types=None,
        partner_ids=None,
        tag_ids=None,
        target_move="posted",
        days_interval=30,
        show_footer=False,
        **kwargs,
    ):
        data = self.aged_get_data(
            date_as_of=date_as_of,
            company_id=company_id,
            account_types=account_types,
            partner_ids=partner_ids,
            tag_ids=tag_ids,
            target_move=target_move,
            days_interval=days_interval,
        )
        bucket_labels = data.get("bucket_labels", [])
        lines = data.get("lines", [])
        currency_symbol = data.get("currency_symbol", "")

        acct_types = account_types or ["receivable"]
        if acct_types == ["payable"]:
            report_title = "Aged Payable"
        else:
            report_title = "Aged Receivable"

        page_height_mm, margin_top_mm, margin_bottom_mm = self._get_page_geometry()
        header_html = self._get_default_header_html(
            request.env.company, report_title
        )

        lines_html = self._render_aged_lines_html(
            lines, bucket_labels, currency_symbol
        )

        is_supplier = False
        use_footer = show_footer and not is_supplier
        footer_html = self._render_footer_html() if use_footer else None
        if not use_footer:
            margin_bottom_mm = 5
        usable_height_mm = round(page_height_mm - margin_top_mm - margin_bottom_mm, 1)

        as_of_display = self._fmt_date(date_as_of)

        html = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
  body {{ font-family: Arial, sans-serif; font-size: 12px; margin: 0; padding: 0; }}
  .page-wrapper {{ box-sizing: border-box; padding: 0px 20px 20px; }}
  table.data-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
  table.data-table th, table.data-table td {{ border: 1px solid #ccc; padding: 4px 6px; font-size: 11px; }}
  table.data-table th {{ background: #f0f0f0; text-align: left; }}
  .right {{ text-align: right; }}
  .bold {{ font-weight: bold; }}
  .group-row {{ background: #e8e8e8; font-weight: bold; }}
  .total-row {{ background: #d0d0d0; font-weight: bold; }}
  .sub-row {{ color: #333; }}
  .period {{ width: 100%; box-sizing: border-box; margin: 0 0 10px; padding: 6px 0;
             background: #f0f0f0; font-size: 11px; color: #333; text-align: center; }}
  .partner-section {{ margin-bottom: 16px; }}
  .partner-section-title {{ font-size: 13px; font-weight: bold; color: #222;
                            margin: 0 0 4px; padding: 4px 8px;
                            background: #e0e0e0; border-left: 3px solid #555; }}
</style>
</head>
<body>
<div class="page-wrapper">
  <div class="report-content">
    {header}
    <div class="period">As of {date_as_of}</div>
    {lines}
  </div>
</div>
</body>
</html>""".format(
            header=header_html,
            date_as_of=as_of_display,
            lines=lines_html,
            usable_height=usable_height_mm,
        )

        portrait_paperformat = request.env.ref(
            "partner_ledger_enterprise_view.paperformat_partner_ledger",
            raise_if_not_found=False,
        )
        report_obj = request.env["ir.actions.report"]
        if portrait_paperformat:
            report_obj = report_obj.new({"paperformat_id": portrait_paperformat.id})
        pdf_content = report_obj._run_wkhtmltopdf(
            [html],
            landscape=False,
            footer=footer_html or "",
            specific_paperformat_args={
                "data-report-margin-top": margin_top_mm,
                "data-report-margin-bottom": margin_bottom_mm,
                "data-report-margin-left": 8,
                "data-report-margin-right": 8,
                "data-report-header-spacing": 0,
            },
        )
        acct_types_for_file = account_types or ["receivable"]
        file_prefix = "Aged_Payable" if acct_types_for_file == ["payable"] else "Aged_Receivable"
        return {
            "file_content": base64.b64encode(pdf_content).decode("utf-8"),
            "file_name": "%s_%s.pdf" % (file_prefix, date_as_of or "report"),
        }

    # ------------------------------------------------------------------
    # /pl/aged/export_excel
    # ------------------------------------------------------------------
    @http.route("/pl/aged/export_excel", type="json", auth="user")
    def aged_export_excel(
        self,
        date_as_of,
        company_id=None,
        account_types=None,
        partner_ids=None,
        tag_ids=None,
        target_move="posted",
        days_interval=30,
        **kwargs,
    ):
        data = self.aged_get_data(
            date_as_of=date_as_of,
            company_id=company_id,
            account_types=account_types,
            partner_ids=partner_ids,
            tag_ids=tag_ids,
            target_move=target_move,
            days_interval=days_interval,
        )
        bucket_labels = data.get("bucket_labels", [])
        lines = data.get("lines", [])

        total_line = None
        body_lines = lines
        if lines and lines[0].get("line_type") == "total":
            total_line = lines[0]
            body_lines = lines[1:]

        rows = []
        for line in body_lines:
            rows.append(line)
            rows.extend(line.get("children") or [])
        if total_line:
            rows.append(total_line)

        headers = ["Partner / Entry", "Invoice Date", "Reference"] + bucket_labels + ["Total"]

        def cell_values(line):
            name = line.get("name") or ""
            if line.get("line_type") == "total":
                name = "Total"
            elif line.get("line_type") == "partner":
                name = line.get("name") or ""

            vals = [name]
            if line.get("line_type") == "account":
                vals.append(self._fmt_date(line.get("invoice_date")))
                vals.append(line.get("reference") or "")
            elif line.get("line_type") == "total":
                vals.append("")
                vals.append("")
            else:
                vals.append("")
                vals.append("")

            buckets = line.get("buckets") or {}
            for i in range(len(bucket_labels)):
                vals.append(round(buckets.get(str(i), 0.0), 2))
            vals.append(round(line.get("total") or line.get("balance") or 0.0, 2))
            return vals

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        worksheet = workbook.add_worksheet("Report")

        header_fmt = workbook.add_format(
            {"bold": True, "bg_color": "#D9D9D9", "border": 1, "valign": "vcenter"}
        )
        group_fmt = workbook.add_format(
            {"bold": True, "bg_color": "#F2F2F2", "border": 1}
        )
        total_fmt = workbook.add_format(
            {"bold": True, "bg_color": "#E0E0E0", "border": 1, "top": 2}
        )
        cell_fmt = workbook.add_format({"border": 1})
        num_fmt = workbook.add_format({"border": 1, "num_format": "#,##0.00"})

        for col, title in enumerate(headers):
            worksheet.write(0, col, title, header_fmt)

        row_idx = 1
        for line in rows:
            lt = line.get("line_type", "")
            fmt = total_fmt if lt == "total" else group_fmt if lt == "partner" else cell_fmt
            values = cell_values(line)
            for col, value in enumerate(values):
                is_num = isinstance(value, (int, float))
                worksheet.write(
                    row_idx, col, value, num_fmt if is_num else fmt
                )
            row_idx += 1

        col_widths = [30, 13, 22] + [14] * len(bucket_labels) + [14]
        for col, w in enumerate(col_widths):
            if col < len(headers):
                worksheet.set_column(col, col, w)
        worksheet.freeze_panes(1, 0)
        worksheet.autofilter(0, 0, max(0, row_idx - 1), len(headers) - 1)

        workbook.close()
        file_content = output.getvalue()
        acct_types = account_types or ["receivable"]
        file_prefix = "Aged_Payable" if acct_types == ["payable"] else "Aged_Receivable"
        return {
            "file_content": base64.b64encode(file_content).decode("utf-8"),
            "file_name": "%s_%s.xlsx" % (file_prefix, date_as_of or "report"),
        }

    # ------------------------------------------------------------------
    # HTML rendering helpers for aged receivable
    # ------------------------------------------------------------------
    def _render_aged_lines_html(self, lines, bucket_labels, currency_symbol):
        """Render aged receivable lines as HTML."""
        num_cols = len(bucket_labels)

        thead_cells = "".join(
            "<th class='right'>%s</th>" % lbl for lbl in bucket_labels
        )
        thead = (
            "<tr>"
            "<th>Partner / Entry</th>"
            "<th>Invoice Date</th>"
            "<th>Reference</th>"
            + thead_cells +
            "<th class='right'>Total</th>"
            "</tr>"
        )

        def render_detail(line):
            name = line.get("name", "")
            bal = line.get("balance") or 0.0
            bucket = line.get("bucket", "0")
            buckets = line.get("buckets") or {}

            cells = (
                "<td style='padding-left:24px;'>%s</td>" % name
                + "<td>%s</td>" % self._fmt_date(line.get("invoice_date"))
                + "<td>%s</td>" % (line.get("reference") or "")
            )
            for i in range(num_cols):
                val = 0.0
                if str(i) == bucket:
                    val = bal
                cells += "<td class='right'>%s</td>" % self._fmt_num(val)
            cells += "<td class='right'><b>%s %s</b></td>" % (
                self._fmt_num(bal),
                currency_symbol,
            )
            return "<tr class='sub-row'>%s</tr>\n" % cells

        def render_partner_total(buckets, total):
            cells = (
                "<td><b>Total</b></td>"
                "<td></td>"
                "<td></td>"
            )
            for i in range(num_cols):
                val = buckets.get(str(i), 0.0)
                cells += "<td class='right'><b>%s</b></td>" % self._fmt_num(val)
            cells += "<td class='right'><b>%s %s</b></td>" % (
                self._fmt_num(total),
                currency_symbol,
            )
            return "<tr class='total-row'>%s</tr>\n" % cells

        body_lines = lines
        if lines and lines[0].get("line_type") == "total":
            body_lines = lines[1:]

        partner_groups = [
            ln for ln in body_lines if ln.get("line_type") == "partner"
        ]

        html_parts = []
        total_line = lines[0] if lines and lines[0].get("line_type") == "total" else None

        if total_line:
            html_parts.append(
                "<table class='data-table'><thead>%s</thead><tbody>" % thead
            )
            html_parts.append(
                render_partner_total(
                    total_line.get("buckets", {}),
                    total_line.get("total", 0.0),
                )
            )
            html_parts.append("</tbody></table>")

        single_partner = len(partner_groups) == 1
        for group in partner_groups:
            pname = group.get("name", "")
            children = group.get("children") or []

            if pname and not single_partner:
                html_parts.append(
                    "<div class='partner-section'>"
                    "<h3 class='partner-section-title'>%s</h3>" % pname
                )
            html_parts.append(
                "<table class='data-table'><thead>%s</thead><tbody>" % thead
            )
            for child in children:
                html_parts.append(render_detail(child))
            html_parts.append(
                render_partner_total(
                    group.get("buckets", {}),
                    group.get("total", 0.0),
                )
            )
            html_parts.append("</tbody></table>")
            if pname and not single_partner:
                html_parts.append("</div>")

        return "\n".join(html_parts)