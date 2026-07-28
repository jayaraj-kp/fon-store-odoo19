# Copyright 2024 Custom Development
# License: LGPL-3.0 or later
#
# Override the OCA General Ledger XLSX report to produce a clean,
# enterprise-style spreadsheet matching Image 3:
#   - No filter header box
#   - Columns: Code | Account Name | Date | Partner | Debit | Credit | Balance
#   - Account header rows in bold with totals (no fill color)
#   - Move lines indented under each account
#   - Running balance per line

from odoo import models


class GeneralLedgerXslxEnterprise(models.AbstractModel):
    _name = "report.a_f_r.report_general_ledger_xlsx"
    _description = "General Ledger XLSX Report – Enterprise Style"
    _inherit = "report.a_f_r.report_general_ledger_xlsx"

    # -------------------------------------------------------------------------
    # Column definition – Image 3 style
    # -------------------------------------------------------------------------
    def _get_report_columns(self, report):
        return {
            0: {"header": "Code",         "field": "code",         "width": 12},
            1: {"header": "Account Name", "field": "name",         "width": 45},
            2: {"header": "Date",         "field": "date",         "width": 12},
            3: {"header": "Partner",      "field": "partner_name", "width": 30},
            4: {
                "header": "Debit",
                "field": "debit",
                "field_initial_balance": "initial_debit",
                "field_final_balance": "final_debit",
                "type": "amount",
                "width": 16,
            },
            5: {
                "header": "Credit",
                "field": "credit",
                "field_initial_balance": "initial_credit",
                "field_final_balance": "final_credit",
                "type": "amount",
                "width": 16,
            },
            6: {
                "header": "Balance",
                "field": "balance",
                "field_initial_balance": "initial_balance",
                "field_final_balance": "final_balance",
                "type": "amount",
                "width": 16,
            },
        }

    # -------------------------------------------------------------------------
    # Suppress the yellow filter table at the top
    # -------------------------------------------------------------------------
    def _write_filters(self, filters, report_data):
        """Do not write any filter rows – keep the sheet clean."""
        pass

    # -------------------------------------------------------------------------
    # Main content generator
    # -------------------------------------------------------------------------
    def _generate_report_content(self, workbook, report, data, report_data):
        res_data = self.env[
            "report.account_financial_report.general_ledger"
        ]._get_report_values(report, data)

        general_ledger = res_data["general_ledger"]
        accounts_data = res_data["accounts_data"]
        journals_data = res_data["journals_data"]
        foreign_currency = res_data["foreign_currency"]
        company_currency = res_data["company_currency"]

        sheet = report_data["sheet"]
        fmts = report_data["formats"]

        # Extra formats we need
        fmt_account_header = workbook.add_format({
            "bold": True,
            "font_size": 11,
            "border": 0,
            "bottom": 1,
            "top": 1,
        })
        fmt_account_header.set_num_format(
            "#,##0." + "0" * company_currency.decimal_places
        )

        fmt_account_name = workbook.add_format({
            "bold": True,
            "font_size": 11,
        })

        fmt_line_indent = workbook.add_format({
            "indent": 1,
        })
        fmt_date = workbook.add_format({"align": "center"})
        fmt_amount = workbook.add_format()
        fmt_amount.set_num_format(
            "#,##0." + "0" * company_currency.decimal_places
        )
        fmt_ending = workbook.add_format({
            "bold": True,
            "italic": True,
        })
        fmt_ending.set_num_format(
            "#,##0." + "0" * company_currency.decimal_places
        )

        # Write column headers once at the top
        self.write_array_header(report_data)

        for account in general_ledger:
            acc_info = accounts_data[account["id"]]
            acc_code = account["code"]
            acc_name = acc_info["name"]

            row = report_data["row_pos"]

            # ------------------------------------------------------------------
            # Account header row  (Code | Name | empty | empty | Debit | Credit | Balance)
            # ------------------------------------------------------------------
            sheet.write(row, 0, acc_code, fmt_account_name)
            sheet.write(row, 1, acc_name, fmt_account_name)
            sheet.write(row, 2, "", fmt_account_header)
            sheet.write(row, 3, "", fmt_account_header)
            # Totals for the account
            fin_debit = account["fin_bal"].get("debit", 0.0)
            fin_credit = account["fin_bal"].get("credit", 0.0)
            fin_balance = account["fin_bal"].get("balance", 0.0)
            sheet.write_number(row, 4, float(fin_debit),   fmt_account_header)
            sheet.write_number(row, 5, float(fin_credit),  fmt_account_header)
            sheet.write_number(row, 6, float(fin_balance), fmt_account_header)
            report_data["row_pos"] += 1

            # ------------------------------------------------------------------
            # Move lines
            # ------------------------------------------------------------------
            if "list_grouped" not in account:
                running_balance = account["init_bal"].get("balance", 0.0)
                for line in account.get("move_lines", []):
                    running_balance += line["debit"] - line["credit"]
                    row = report_data["row_pos"]

                    # Resolve journal
                    jnl = journals_data.get(line.get("journal_id"), {})

                    entry_label = line.get("entry", "")
                    ref_label = line.get("ref_label", "")
                    # Combine entry + ref_label for display
                    if ref_label and ref_label != entry_label:
                        display_entry = f"{entry_label}  {ref_label}"
                    else:
                        display_entry = entry_label

                    # col 0 = blank (account code cell already written in header)
                    sheet.write_string(row, 0, "", fmt_line_indent)
                    sheet.write_string(row, 1, display_entry)
                    # Date
                    date_val = line.get("date")
                    if date_val:
                        sheet.write_string(
                            row, 2,
                            date_val.strftime("%m/%d/%Y") if hasattr(date_val, "strftime") else str(date_val),
                            fmt_date,
                        )
                    else:
                        sheet.write_string(row, 2, "")
                    # Partner
                    sheet.write_string(row, 3, line.get("partner_name") or "")
                    # Debit / Credit
                    sheet.write_number(row, 4, float(line.get("debit", 0.0)), fmt_amount)
                    sheet.write_number(row, 5, float(line.get("credit", 0.0)), fmt_amount)
                    # Running balance
                    sheet.write_number(row, 6, float(running_balance), fmt_amount)
                    report_data["row_pos"] += 1

            # blank row between accounts
            report_data["row_pos"] += 1

    # -------------------------------------------------------------------------
    # Column label position helpers (needed by parent write_initial_balance etc.)
    # -------------------------------------------------------------------------
    def _get_col_pos_initial_balance_label(self):
        return 3   # "Partner" column used for label

    def _get_col_count_final_balance_name(self):
        return 4   # merge first 4 columns for the account name

    def _get_col_pos_final_balance_label(self):
        return 3
