# Copyright 2024 Custom Development
# License: LGPL-3.0 or later

import datetime
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class FinancialReportEngine(models.AbstractModel):
    """Build Enterprise-style hierarchical Balance Sheet and P&L lines."""

    _name = "financial.report.engine"
    _description = "Financial Statement Report Engine"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @api.model
    def get_balance_sheet(self, date_to, company_id=None, target_move="posted"):
        company = self._get_company(company_id)
        balances = self._get_account_balances(
            company, date_to=date_to, target_move=target_move, period_mode=False
        )
        lines = self._build_balance_sheet_lines(balances, company)
        return {
            "lines": lines,
            "company_name": company.name,
            "currency_name": company.currency_id.name,
            "currency_symbol": company.currency_id.symbol,
            "date_to": date_to,
        }

    @api.model
    def get_profit_and_loss(
        self, date_from, date_to, company_id=None, target_move="posted"
    ):
        company = self._get_company(company_id)
        balances = self._get_account_balances(
            company,
            date_from=date_from,
            date_to=date_to,
            target_move=target_move,
            period_mode=True,
        )
        lines = self._build_profit_and_loss_lines(balances, company)
        return {
            "lines": lines,
            "company_name": company.name,
            "currency_name": company.currency_id.name,
            "currency_symbol": company.currency_id.symbol,
            "date_from": date_from,
            "date_to": date_to,
        }

    @api.model
    def has_unposted_entries(self, date_to, company_id=None):
        company = self._get_company(company_id)
        try:
            date_to_obj = datetime.date.fromisoformat(date_to)
        except Exception:
            date_to_obj = datetime.date.today()
        count = self.env["account.move"].search_count(
            [
                ("company_id", "=", company.id),
                ("state", "=", "draft"),
                ("date", "<=", date_to_obj),
            ]
        )
        return count > 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_company(self, company_id):
        if company_id:
            return self.env["res.company"].browse(int(company_id))
        return self.env.company

    def _move_state_domain(self, target_move):
        if target_move == "posted":
            return [("move_id.state", "=", "posted")]
        return [("move_id.state", "!=", "cancel")]

    def _get_outstanding_account_ids(self, company):
        journals = self.env["account.journal"].search(
            [("company_id", "=", company.id), ("type", "in", ["bank", "cash"])]
        )
        accounts = (
            journals.mapped("inbound_payment_method_line_ids.payment_account_id")
            | journals.mapped("outbound_payment_method_line_ids.payment_account_id")
        )
        return accounts.ids

    def _get_account_balances(
        self, company, date_to, target_move="posted", date_from=None, period_mode=False
    ):
        """Return {account_id: raw_balance} where raw = sum(debit)-sum(credit)."""
        try:
            date_to_obj = datetime.date.fromisoformat(date_to)
        except Exception:
            date_to_obj = datetime.date.today()

        domain = [
            ("company_id", "=", company.id),
            ("display_type", "not in", ["line_section", "line_note"]),
            ("date", "<=", date_to_obj),
        ] + self._move_state_domain(target_move)

        if period_mode and date_from:
            try:
                date_from_obj = datetime.date.fromisoformat(date_from)
                domain.append(("date", ">=", date_from_obj))
            except Exception:
                pass

        groups = self.env["account.move.line"].read_group(
            domain,
            ["account_id", "debit:sum", "credit:sum"],
            ["account_id"],
        )

        result = {}
        for group in groups:
            if not group.get("account_id"):
                continue
            acc_id = group["account_id"][0]
            debit = group.get("debit") or 0.0
            credit = group.get("credit") or 0.0
            result[acc_id] = debit - credit
        return result

    def _load_accounts_info(self, account_ids):
        if not account_ids:
            return {}
        records = self.env["account.account"].search_read(
            [("id", "in", list(account_ids))],
            ["id", "code", "name", "account_type"],
        )
        return {r["id"]: r for r in records}

    def _accounts_by_types(self, balances, accounts_info, account_types, exclude_ids=None):
        exclude_ids = set(exclude_ids or [])
        matched = []
        for acc_id, raw_bal in balances.items():
            if acc_id in exclude_ids:
                continue
            info = accounts_info.get(acc_id)
            if not info or info.get("account_type") not in account_types:
                continue
            matched.append((acc_id, info, raw_bal))
        matched.sort(key=lambda x: x[1].get("code") or "")
        return matched

    def _display_asset(self, raw_balance):
        return round(raw_balance, 2)

    def _display_liability(self, raw_balance):
        return round(-raw_balance, 2)

    def _display_income(self, raw_balance):
        return round(-raw_balance, 2)

    def _display_expense(self, raw_balance):
        return round(raw_balance, 2)

    def _sum_display(self, items, display_fn):
        return round(sum(display_fn(v) for _, _, v in items), 2)

    def _account_lines(self, matched, display_fn, parent_key):
        lines = []
        for acc_id, info, raw_bal in matched:
            balance = display_fn(raw_bal)
            if abs(balance) < 0.005:
                continue
            lines.append(
                {
                    "id": f"{parent_key}_acc_{acc_id}",
                    "name": f"{info.get('code', '')} {info.get('name', '')}".strip(),
                    "line_type": "account",
                    "style": "account",
                    "level": 3,
                    "balance": balance,
                    "account_id": acc_id,
                    "children": [],
                }
            )
        return lines

    def _section_line(self, key, name, balance, style="section", level=0, children=None):
        return {
            "id": key,
            "name": name,
            "line_type": "section",
            "style": style,
            "level": level,
            "balance": round(balance, 2),
            "children": children or [],
        }

    def _subtotal_line(self, key, name, balance, level=0):
        return {
            "id": key,
            "name": name,
            "line_type": "subtotal",
            "style": "subtotal",
            "level": level,
            "balance": round(balance, 2),
            "children": [],
        }

    def _rollup_balance(self, line):
        if line.get("children"):
            total = sum(self._rollup_balance(child) for child in line["children"])
            line["balance"] = round(total, 2)
            return line["balance"]
        return line.get("balance") or 0.0

    # ------------------------------------------------------------------
    # Balance Sheet
    # ------------------------------------------------------------------

    def _build_balance_sheet_lines(self, balances, company):
        account_ids = set(balances.keys())
        accounts_info = self._load_accounts_info(account_ids)
        outstanding_ids = self._get_outstanding_account_ids(company)

        # --- ASSETS ---
        bank_cash_types = ["asset_cash"]
        bank_cash = self._accounts_by_types(
            balances, accounts_info, bank_cash_types, exclude_ids=outstanding_ids
        )
        outstanding = self._accounts_by_types(
            balances,
            accounts_info,
            list(bank_cash_types) + ["asset_current", "asset_receivable"],
        )
        outstanding = [
            (aid, info, bal)
            for aid, info, bal in outstanding
            if aid in outstanding_ids
        ]

        receivables = self._accounts_by_types(
            balances,
            accounts_info,
            ["asset_receivable"],
            exclude_ids=outstanding_ids,
        )
        prepayments = self._accounts_by_types(
            balances, accounts_info, ["asset_prepayments"]
        )
        other_current = self._accounts_by_types(
            balances,
            accounts_info,
            ["asset_current"],
            exclude_ids=outstanding_ids,
        )

        bank_children = self._account_lines(
            bank_cash + outstanding, self._display_asset, "bank_cash"
        )
        bank_section = self._section_line(
            "bank_cash",
            "Bank and Cash",
            self._sum_display(bank_cash + outstanding, self._display_asset),
            style="subsection",
            level=2,
            children=bank_children,
        )

        recv_section = self._section_line(
            "receivables",
            "Receivables",
            self._sum_display(receivables, self._display_asset),
            style="subsection",
            level=2,
            children=self._account_lines(receivables, self._display_asset, "recv"),
        )
        prep_section = self._section_line(
            "prepayments",
            "Prepayments",
            self._sum_display(prepayments, self._display_asset),
            style="subsection",
            level=2,
            children=self._account_lines(prepayments, self._display_asset, "prep"),
        )
        other_current_section = self._section_line(
            "other_current_assets",
            "Other Current Assets",
            self._sum_display(other_current, self._display_asset),
            style="subsection",
            level=2,
            children=self._account_lines(
                other_current, self._display_asset, "other_ca"
            ),
        )

        current_asset_children = [
            s
            for s in [bank_section, recv_section, prep_section, other_current_section]
            if s["balance"] or s["children"]
        ]
        current_assets = self._section_line(
            "current_assets",
            "Current Assets",
            0,
            style="group",
            level=1,
            children=current_asset_children,
        )
        self._rollup_balance(current_assets)

        fixed = self._accounts_by_types(balances, accounts_info, ["asset_fixed"])
        fixed_section = self._section_line(
            "fixed_assets",
            "Fixed Assets",
            self._sum_display(fixed, self._display_asset),
            style="group",
            level=1,
            children=self._account_lines(fixed, self._display_asset, "fixed"),
        )

        non_current = self._accounts_by_types(
            balances, accounts_info, ["asset_non_current"]
        )
        non_current_section = self._section_line(
            "non_current_assets",
            "Non-current Assets",
            self._sum_display(non_current, self._display_asset),
            style="group",
            level=1,
            children=self._account_lines(
                non_current, self._display_asset, "nca"
            ),
        )

        asset_children = [
            s
            for s in [current_assets, fixed_section, non_current_section]
            if s["balance"] or s["children"]
        ]
        assets = self._section_line(
            "assets",
            "ASSETS",
            0,
            style="header",
            level=0,
            children=asset_children,
        )
        self._rollup_balance(assets)

        # --- LIABILITIES ---
        credit_card = self._accounts_by_types(
            balances, accounts_info, ["liability_credit_card"]
        )
        payables = self._accounts_by_types(
            balances,
            accounts_info,
            ["liability_payable"],
            exclude_ids=outstanding_ids,
        )
        other_current_liab = self._accounts_by_types(
            balances,
            accounts_info,
            ["liability_current"],
            exclude_ids=outstanding_ids,
        )

        cc_section = self._section_line(
            "credit_card",
            "Credit Card",
            self._sum_display(credit_card, self._display_liability),
            style="subsection",
            level=2,
            children=self._account_lines(
                credit_card, self._display_liability, "cc"
            ),
        )
        pay_section = self._section_line(
            "payables",
            "Payables",
            self._sum_display(payables, self._display_liability),
            style="subsection",
            level=2,
            children=self._account_lines(payables, self._display_liability, "pay"),
        )
        ocl_section = self._section_line(
            "other_current_liab",
            "Other Current Liabilities",
            self._sum_display(other_current_liab, self._display_liability),
            style="subsection",
            level=2,
            children=self._account_lines(
                other_current_liab, self._display_liability, "ocl"
            ),
        )

        current_liab_children = [
            s for s in [cc_section, pay_section, ocl_section] if s["balance"] or s["children"]
        ]
        current_liabilities = self._section_line(
            "current_liabilities",
            "Current Liabilities",
            0,
            style="group",
            level=1,
            children=current_liab_children,
        )
        self._rollup_balance(current_liabilities)

        non_current_liab = self._accounts_by_types(
            balances, accounts_info, ["liability_non_current"]
        )
        non_current_liab_section = self._section_line(
            "non_current_liabilities",
            "Non-current Liabilities",
            self._sum_display(non_current_liab, self._display_liability),
            style="group",
            level=1,
            children=self._account_lines(
                non_current_liab, self._display_liability, "ncl"
            ),
        )

        liab_children = [
            s
            for s in [current_liabilities, non_current_liab_section]
            if s["balance"] or s["children"]
        ]
        liabilities = self._section_line(
            "liabilities",
            "LIABILITIES",
            0,
            style="header",
            level=0,
            children=liab_children,
        )
        self._rollup_balance(liabilities)

        # --- EQUITY ---
        equity_accounts = self._accounts_by_types(balances, accounts_info, ["equity"])
        unaffected = self._accounts_by_types(
            balances, accounts_info, ["equity_unaffected"]
        )

        prev_year_accs = [
            (aid, info, bal)
            for aid, info, bal in equity_accounts
            if "retained" in (info.get("name") or "").lower()
            or "previous" in (info.get("name") or "").lower()
        ]
        prev_year_ids = {aid for aid, _, _ in prev_year_accs}
        regular_equity_accs = [
            (aid, info, bal)
            for aid, info, bal in equity_accounts
            if aid not in prev_year_ids
        ]

        equity_section = self._section_line(
            "equity",
            "Equity",
            self._sum_display(regular_equity_accs, self._display_liability),
            style="group",
            level=1,
            children=self._account_lines(
                regular_equity_accs, self._display_liability, "eq"
            ),
        )

        current_year_bal = self._sum_display(unaffected, self._display_liability)
        current_year = self._section_line(
            "current_year_earnings",
            "Current Year Unallocated Earnings",
            current_year_bal,
            style="account",
            level=2,
            children=[],
        )
        current_year["line_type"] = "computed"

        prev_year_balance = self._sum_display(prev_year_accs, self._display_liability)
        prev_year = self._section_line(
            "previous_years_earnings",
            "Previous Years Earnings",
            prev_year_balance,
            style="account",
            level=2,
            children=[],
        )
        prev_year["line_type"] = "computed"

        earnings = self._section_line(
            "earnings",
            "Earnings",
            0,
            style="group",
            level=1,
            children=[current_year, prev_year],
        )
        self._rollup_balance(earnings)

        equity_children = [
            s for s in [equity_section, earnings] if s["balance"] or s["children"]
        ]
        equity = self._section_line(
            "equity_section",
            "EQUITY (& EARNINGS)",
            0,
            style="header",
            level=0,
            children=equity_children,
        )
        self._rollup_balance(equity)

        liab_equity_total = self._subtotal_line(
            "liabilities_equity",
            "LIABILITIES + EQUITY",
            liabilities["balance"] + equity["balance"],
            level=0,
        )

        return [assets, liabilities, equity, liab_equity_total]

    # ------------------------------------------------------------------
    # Profit & Loss
    # ------------------------------------------------------------------

    def _build_profit_and_loss_lines(self, balances, company):
        account_ids = set(balances.keys())
        accounts_info = self._load_accounts_info(account_ids)

        cor_types = ["expense_direct_cost"]
        opex_types = ["expense", "expense_depreciation"]
        other_income_types = ["income_other"]
        allocation_types = ["equity"]

        revenue_accs = self._accounts_by_types(balances, accounts_info, ["income"])
        cor_accs = self._accounts_by_types(balances, accounts_info, cor_types)
        opex_accs = self._accounts_by_types(balances, accounts_info, opex_types)
        other_income_accs = self._accounts_by_types(
            balances, accounts_info, other_income_types
        )
        allocation_accs = self._accounts_by_types(
            balances, accounts_info, allocation_types
        )

        revenue_total = self._sum_display(revenue_accs, self._display_income)
        cor_total = self._sum_display(cor_accs, self._display_expense)
        opex_total = self._sum_display(opex_accs, self._display_expense)

        revenue_children = self._account_lines(
            revenue_accs, self._display_income, "rev"
        )
        cor_line = self._section_line(
            "cost_of_revenue",
            "Costs of Revenue",
            cor_total,
            style="subsection",
            level=1,
            children=self._account_lines(cor_accs, self._display_expense, "cor"),
        )
        if cor_total or cor_line["children"]:
            revenue_children.append(cor_line)

        revenue = self._section_line(
            "revenue",
            "Revenue",
            revenue_total,
            style="group",
            level=0,
            children=revenue_children,
        )

        gross_profit = self._subtotal_line(
            "gross_profit", "Gross Profit", revenue_total - cor_total, level=0
        )

        opex = self._section_line(
            "operating_expenses",
            "Operating Expenses",
            opex_total,
            style="group",
            level=0,
            children=self._account_lines(opex_accs, self._display_expense, "opex"),
        )

        operating_income = self._subtotal_line(
            "operating_income",
            "Operating Income (or Loss)",
            gross_profit["balance"] - opex_total,
            level=0,
        )

        other_income_total = self._sum_display(
            other_income_accs, self._display_income
        )
        other_income = self._section_line(
            "other_income",
            "Other Income",
            other_income_total,
            style="group",
            level=0,
            children=self._account_lines(
                other_income_accs, self._display_income, "oi"
            ),
        )

        other_expense = self._section_line(
            "other_expenses",
            "Other Expenses",
            0,
            style="group",
            level=0,
            children=[],
        )

        net_profit = self._subtotal_line(
            "net_profit",
            "Net Profit",
            operating_income["balance"]
            + other_income_total
            - other_expense["balance"],
            level=0,
        )

        alloc_total = self._sum_display(allocation_accs, self._display_expense)
        allocations = self._section_line(
            "allocations",
            "Allocations and Withdrawals",
            alloc_total,
            style="group",
            level=0,
            children=self._account_lines(
                allocation_accs, self._display_expense, "alloc"
            ),
        )

        net_after_alloc = self._subtotal_line(
            "net_after_alloc",
            "Net Profit Left After Allocations and Withdrawals",
            net_profit["balance"] - alloc_total,
            level=0,
        )

        return [
            revenue,
            gross_profit,
            opex,
            operating_income,
            other_income,
            other_expense,
            net_profit,
            allocations,
            net_after_alloc,
        ]

    @api.model
    def merge_comparison_lines(self, current_lines, comparison_lines):
        """Attach comparison_balance to matching line ids recursively."""
        comp_map = {}

        def _flatten(lines):
            for line in lines:
                comp_map[line["id"]] = line.get("balance", 0.0)
                if line.get("children"):
                    _flatten(line["children"])

        _flatten(comparison_lines)

        def _merge(lines):
            for line in lines:
                line["comparison_balance"] = comp_map.get(line["id"], 0.0)
                if line.get("children"):
                    _merge(line["children"])

        _merge(current_lines)
        return current_lines

    @api.model
    def merge_multi_comparison_lines(self, current_lines, comparison_periods):
        """Attach comparison_balances list to each line for multi-period comparison."""
        period_maps = []
        for period in comparison_periods:
            comp_map = {}

            def _flatten(lines, _map=comp_map):
                for line in lines:
                    _map[line["id"]] = line.get("balance", 0.0)
                    if line.get("children"):
                        _flatten(line["children"])

            _flatten(period["lines"])
            period_maps.append(
                {
                    "label": period.get("label", ""),
                    "date_to": period.get("date_to", ""),
                    "date_from": period.get("date_from", ""),
                    "balances": comp_map,
                }
            )

        def _merge(lines):
            for line in lines:
                line["comparison_balances"] = [
                    {
                        "label": pm["label"],
                        "date_to": pm["date_to"],
                        "date_from": pm["date_from"],
                        "balance": pm["balances"].get(line["id"], 0.0),
                    }
                    for pm in period_maps
                ]
                # Keep backward compat with single comparison column
                if line["comparison_balances"]:
                    line["comparison_balance"] = line["comparison_balances"][0][
                        "balance"
                    ]
                if line.get("children"):
                    _merge(line["children"])

        _merge(current_lines)
        return current_lines
