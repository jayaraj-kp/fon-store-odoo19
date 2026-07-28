# Copyright 2024 Custom Development
# License: LGPL-3.0 or later

import datetime
import logging
from collections import defaultdict

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class OcaGeneralLedgerController(http.Controller):
    """
    JSON controller for the Enterprise-style General Ledger OWL view.
    Computes GL data on-the-fly using account.move.line reads and
    delegates PDF/XLSX export to OCA's existing wizard infrastructure.
    """

    # ------------------------------------------------------------------
    # /oca_gl/init  – returns filter options (journals, companies)
    # ------------------------------------------------------------------
    @http.route("/oca_gl/init", type="json", auth="user")
    def get_init_data(self, company_id=None):
        env = request.env
        company = (
            env["res.company"].browse(int(company_id))
            if company_id
            else env.company
        )

        # Available journals for this company
        journals = env["account.journal"].search_read(
            [("company_id", "=", company.id)],
            ["id", "name", "code", "type"],
            order="name",
        )

        # All companies the user can access
        companies = env["res.company"].search_read(
            [("id", "in", env.user.company_ids.ids)],
            ["id", "name"],
            order="name",
        )

        # Default date range: first day of current year → today
        today_date = datetime.date.today()
        date_from = today_date.replace(month=1, day=1).isoformat()
        date_to = today_date.isoformat()

        return {
            "journals": journals,
            "companies": companies,
            "currency_name": company.currency_id.name,
            "currency_symbol": company.currency_id.symbol,
            "company_id": company.id,
            "company_name": company.name,
            "date_from": date_from,
            "date_to": date_to,
        }

    # ------------------------------------------------------------------
    # /oca_gl/get_data  – main data endpoint
    # ------------------------------------------------------------------
    @http.route("/oca_gl/get_data", type="json", auth="user")
    def get_data(
        self,
        date_from,
        date_to,
        company_id=None,
        journal_ids=None,
        target_move="posted",
        hide_account_at_0=False,
        account_ids=None,
        partner_ids=None,
        grouped_by="none",
        **kwargs,
    ):
        env = request.env
        company = (
            env["res.company"].browse(int(company_id))
            if company_id
            else env.company
        )

        # ---- Build domain helpers ----------------------------------------
        # Parse ISO date strings to datetime.date objects for safe DB query comparisons
        try:
            date_from_obj = datetime.date.fromisoformat(date_from)
            date_to_obj = datetime.date.fromisoformat(date_to)
        except Exception:
            date_from_obj = datetime.date.today().replace(month=1, day=1)
            date_to_obj = datetime.date.today()

        def _base_domain():
            d = [
                ("company_id", "=", company.id),
                (
                    "display_type",
                    "not in",
                    ["line_section", "line_note"],
                ),
            ]
            if target_move == "posted":
                d.append(("move_id.state", "=", "posted"))
            if journal_ids:
                j_ids = [int(x) for x in journal_ids if x]
                if j_ids:
                    d.append(("journal_id", "in", j_ids))
            if account_ids:
                a_ids = [int(x) for x in account_ids if x]
                if a_ids:
                    d.append(("account_id", "in", a_ids))
            if partner_ids:
                p_ids = [int(x) for x in partner_ids if x]
                if p_ids:
                    d.append(("partner_id", "in", p_ids))
            return d

        period_domain = _base_domain() + [
            ("date", ">=", date_from_obj),
            ("date", "<=", date_to_obj),
        ]

        init_domain = _base_domain() + [
            ("date", "<", date_from_obj),
        ]

        # ---- Read initial balances grouped by account --------------------
        init_groups = []
        try:
            init_groups = env["account.move.line"].read_group(
                init_domain,
                ["account_id", "debit:sum", "credit:sum"],
                ["account_id"],
            )
        except Exception as e:
            _logger.error("Error reading initial balances: %s", e)

        init_by_account = {}
        for g in init_groups:
            if g.get("account_id"):
                acc_id = g["account_id"][0]
                init_by_account[acc_id] = {
                    "debit": g.get("debit", 0.0) or 0.0,
                    "credit": g.get("credit", 0.0) or 0.0,
                }

        # ---- Read period move lines --------------------------------------
        fields_to_read = [
            "account_id",
            "date",
            "move_id",
            "journal_id",
            "partner_id",
            "name",
            "ref",
            "debit",
            "credit",
            "amount_currency",
            "currency_id",
            "matching_number",
        ]
        move_lines = []
        try:
            move_lines = env["account.move.line"].search_read(
                period_domain,
                fields_to_read,
                order="account_id, date, id",
            )
        except Exception as e:
            _logger.error("Error reading period lines: %s", e)

        # ---- Build account lookup (code + name) -------------------------
        all_account_ids = set(init_by_account.keys())
        for ml in move_lines:
            if ml.get("account_id"):
                all_account_ids.add(ml["account_id"][0])

        accounts_info = {}
        if all_account_ids:
            try:
                acc_records = env["account.account"].search_read(
                    [("id", "in", list(all_account_ids))],
                    ["id", "code", "name"],
                )
                for a in acc_records:
                    accounts_info[a["id"]] = {
                        "code": a["code"],
                        "name": a["name"],
                    }
            except Exception as e:
                _logger.error("Error reading accounts lookup: %s", e)

        # ---- Group move lines by account --------------------------------
        lines_by_account = defaultdict(list)
        for ml in move_lines:
            if ml.get("account_id"):
                lines_by_account[ml["account_id"][0]].append(ml)

        # ---- Build result -----------------------------------------------
        result = []

        # Union of accounts: those with init balance + those with period lines
        for acc_id in sorted(
            all_account_ids,
            key=lambda i: accounts_info.get(i, {}).get("code", "") or "",
        ):
            if acc_id not in accounts_info:
                continue
            acc_info = accounts_info[acc_id]
            code = acc_info.get("code", "")
            name = acc_info.get("name", "")

            init = init_by_account.get(acc_id, {"debit": 0.0, "credit": 0.0})
            init_debit = init["debit"]
            init_credit = init["credit"]
            init_balance = init_debit - init_credit

            period_lines_raw = lines_by_account.get(acc_id, [])

            # Compute cumulative balance and build serializable line list
            cumul_balance = init_balance
            period_debit = 0.0
            period_credit = 0.0
            lines_out = []

            for ml in period_lines_raw:
                line_debit = ml.get("debit") or 0.0
                line_credit = ml.get("credit") or 0.0
                cumul_balance += line_debit - line_credit
                period_debit += line_debit
                period_credit += line_credit

                move_id_val = ml.get("move_id")
                partner_id_val = ml.get("partner_id")
                journal_id_val = ml.get("journal_id")
                currency_id_val = ml.get("currency_id")

                ref_label = ""
                if ml.get("ref") and ml.get("name"):
                    ref_label = f"{ml['ref']} - {ml['name']}"
                elif ml.get("ref"):
                    ref_label = ml["ref"]
                elif ml.get("name"):
                    ref_label = ml["name"]

                lines_out.append(
                    {
                        "id": ml["id"],
                        "date": str(ml["date"]) if ml.get("date") else "",
                        "move_name": move_id_val[1] if move_id_val else "",
                        "move_id": move_id_val[0] if move_id_val else False,
                        "journal": journal_id_val[1] if journal_id_val else "",
                        "journal_id": journal_id_val[0] if journal_id_val else False,
                        "partner": (
                            partner_id_val[1] if partner_id_val else ""
                        ),
                        "partner_id": (
                            partner_id_val[0] if partner_id_val else False
                        ),
                        "ref_label": ref_label,
                        "debit": line_debit,
                        "credit": line_credit,
                        "balance": round(cumul_balance, 2),
                        "amount_currency": ml.get("amount_currency") or 0.0,
                        "currency": (
                            currency_id_val[1] if currency_id_val else ""
                        ),
                        "matching": ml.get("matching_number") or "",
                    }
                )

            final_balance = round(cumul_balance, 2)

            # Optionally skip accounts with zero ending balance and no lines
            if hide_account_at_0 and abs(final_balance) < 0.005 and not lines_out:
                continue

            result.append(
                {
                    "id": acc_id,
                    "code": code,
                    "name": name,
                    "init_bal": {
                        "debit": round(init_debit, 2),
                        "credit": round(init_credit, 2),
                        "balance": round(init_balance, 2),
                    },
                    "fin_bal": {
                        "debit": round(period_debit, 2),
                        "credit": round(period_credit, 2),
                        "balance": final_balance,
                    },
                    "move_lines": lines_out,
                }
            )

        # Company currency info
        currency = company.currency_id
        return {
            "accounts": result,
            "company_name": company.name,
            "currency_name": currency.name,
            "currency_symbol": currency.symbol,
            "date_from": date_from,
            "date_to": date_to,
        }

    # ------------------------------------------------------------------
    # /oca_gl/export  – delegate to OCA wizard export
    # ------------------------------------------------------------------
    @http.route("/oca_gl/export", type="json", auth="user")
    def export(self, export_format, filters):
        """
        Creates a transient OCA wizard with the current filter state,
        then calls button_export_pdf or button_export_xlsx to return
        the report action that the OWL component will execute.
        """
        env = request.env
        report_type = filters.get("report_type", "gl")

        wizard_vals = {
            "date_from": filters.get("date_from"),
            "date_to": filters.get("date_to"),
            "target_move": filters.get("target_move", "posted"),
            "hide_account_at_0": filters.get("hide_account_at_0", False),
        }

        if filters.get("company_id"):
            wizard_vals["company_id"] = int(filters["company_id"])

        if filters.get("journal_ids"):
            wizard_vals["account_journal_ids"] = [
                (6, 0, [int(j) for j in filters["journal_ids"]])
            ]

        if filters.get("account_ids"):
            wizard_vals["account_ids"] = [
                (6, 0, [int(a) for a in filters["account_ids"]])
            ]

        if filters.get("partner_ids"):
            wizard_vals["partner_ids"] = [
                (6, 0, [int(p) for p in filters["partner_ids"]])
            ]

        # Choose the correct OCA wizard based on report type
        if report_type == "tb":
            # Trial Balance uses its own wizard
            tb_vals = {
                "date_from": wizard_vals.get("date_from"),
                "date_to": wizard_vals.get("date_to"),
                "target_move": wizard_vals.get("target_move", "posted"),
                "hide_account_at_0": wizard_vals.get("hide_account_at_0", False),
            }
            if wizard_vals.get("company_id"):
                tb_vals["company_id"] = wizard_vals["company_id"]
            if filters.get("journal_ids"):
                tb_vals["account_journal_ids"] = wizard_vals.get("account_journal_ids")
            if filters.get("account_ids"):
                tb_vals["account_ids"] = wizard_vals.get("account_ids")
            if filters.get("partner_ids"):
                tb_vals["partner_ids"] = wizard_vals.get("partner_ids")
            wizard = env["trial.balance.report.wizard"].create(tb_vals)
        else:
            # General Ledger wizard — include GL-specific fields
            gl_vals = dict(wizard_vals)
            gl_vals["centralize"] = filters.get("centralize", False)
            gl_vals["grouped_by"] = filters.get("grouped_by", "none")
            wizard = env["general.ledger.report.wizard"].create(gl_vals)

        if export_format == "pdf":
            action = wizard.button_export_pdf()
        elif export_format == "xlsx":
            action = wizard.button_export_xlsx()
        else:
            raise ValueError(f"Unknown export format: {export_format}")

        return action



