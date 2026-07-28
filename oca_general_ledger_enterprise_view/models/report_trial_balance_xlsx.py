# Copyright 2024 Custom Development
# License: LGPL-3.0 or later
#
# Override the OCA Trial Balance XLSX report to produce a clean,
# enterprise-style spreadsheet:
#   - No filter header box
#   - Columns: Code | Account | Initial Balance | Debit | Credit | End Balance
#   - Account rows in bold
#   - Grand totals row at the bottom

from odoo import models


class TrialBalanceXslxEnterprise(models.AbstractModel):
    _name = "report.a_f_r.report_trial_balance_xlsx"
    _description = "Trial Balance XLSX Report – Enterprise Style"
    _inherit = "report.a_f_r.report_trial_balance_xlsx"

    # -------------------------------------------------------------------------
    # Column definition
    # -------------------------------------------------------------------------
    def _get_report_columns(self, report):
        return {
            0: {"header": "Code",             "field": "code",            "width": 12},
            1: {"header": "Account",           "field": "name",            "width": 45},
            2: {
                "header": "Initial Balance",
                "field": "initial_balance",
                "type": "amount",
                "width": 18,
            },
            3: {
                "header": "Debit",
                "field": "debit",
                "type": "amount",
                "width": 16,
            },
            4: {
                "header": "Credit",
                "field": "credit",
                "type": "amount",
                "width": 16,
            },
            5: {
                "header": "End Balance",
                "field": "ending_balance",
                "type": "amount",
                "width": 18,
            },
        }

    # -------------------------------------------------------------------------
    # Suppress yellow filter table
    # -------------------------------------------------------------------------
    def _write_filters(self, filters, report_data):
        pass

    # -------------------------------------------------------------------------
    # Main content generator
    # -------------------------------------------------------------------------
    def _generate_report_content(self, workbook, report, data, report_data):
        res_data = self.env[
            "report.account_financial_report.trial_balance"
        ]._get_report_values(report, data)

        trial_balance = res_data["trial_balance"]
        total_amount = res_data.get("total_amount", {})
        company_currency = self.env.company.currency_id

        sheet = report_data["sheet"]
        fmts = report_data["formats"]

        # Extra formats
        fmt_amount = workbook.add_format()
        fmt_amount.set_num_format(
            "#,##0." + "0" * company_currency.decimal_places
        )
        fmt_bold_amount = workbook.add_format({"bold": True, "bottom": 1, "top": 1})
        fmt_bold_amount.set_num_format(
            "#,##0." + "0" * company_currency.decimal_places
        )
        fmt_bold = workbook.add_format({"bold": True, "bottom": 1, "top": 1})

        # Write column headers
        self.write_array_header(report_data)

        for balance in trial_balance:
            row = report_data["row_pos"]
            # Detect if this is a group header row (hierarchy) or leaf account
            is_group = balance.get("level", 99) < 3

            if is_group:
                fmt_str = fmts["format_bold"]
                fmt_num = fmt_bold_amount
            else:
                fmt_str = None
                fmt_num = fmt_amount

            sheet.write_string(row, 0, balance.get("code", "") or "", fmt_str or workbook.add_format())
            sheet.write_string(row, 1, balance.get("name", "") or "", fmt_str or workbook.add_format())

            def write_num(col, val):
                try:
                    v = float(val or 0)
                except (ValueError, TypeError):
                    v = 0.0
                sheet.write_number(row, col, v, fmt_num if is_group else fmt_amount)

            write_num(2, balance.get("initial_balance", 0.0))
            write_num(3, balance.get("debit", 0.0))
            write_num(4, balance.get("credit", 0.0))
            write_num(5, balance.get("ending_balance", 0.0))

            report_data["row_pos"] += 1

        # Grand total row
        report_data["row_pos"] += 1
        row = report_data["row_pos"]
        sheet.write_string(row, 0, "", fmt_bold)
        sheet.write_string(row, 1, "TOTAL", fmt_bold)

        totals = {
            "initial_balance": 0.0,
            "debit": 0.0,
            "credit": 0.0,
            "ending_balance": 0.0,
        }
        for b in trial_balance:
            if b.get("level", 0) >= 2:  # only leaf accounts for totals
                for k in totals:
                    try:
                        totals[k] += float(b.get(k, 0) or 0)
                    except (ValueError, TypeError):
                        pass

        for col, field in enumerate(
            ["initial_balance", "debit", "credit", "ending_balance"], start=2
        ):
            sheet.write_number(row, col, totals[field], fmt_bold_amount)
        report_data["row_pos"] += 1

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    def _get_col_count_filter_name(self):
        return 2

    def _get_col_count_filter_value(self):
        return 3
