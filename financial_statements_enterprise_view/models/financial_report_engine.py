import datetime
import logging
from collections import defaultdict

from odoo import api, models, _
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import SQL

_logger = logging.getLogger(__name__)


class FinancialReportEngine(models.AbstractModel):
    """Build Enterprise-style hierarchical Balance Sheet, P&L and VAT lines."""

    _name = "financial.report.engine"
    _description = "Financial Statement Report Engine"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @api.model
    def get_balance_sheet(
            self, date_to, company_id=None, target_move="posted",
            analytic_account_ids=None, with_debit_credit=False
    ):
        self._check_access()
        if date_to:
            self._parse_date_or_raise(date_to, "date_to")
        company = self._get_company(company_id)
        self = self._scoped_to(company)  # FIX (multi-company)
        # FIX: round to this company's currency precision, not a
        # hardcoded 2 decimals — see _round_digits() above.
        digits = company.currency_id.decimal_places if company.currency_id else 2
        self = self.with_context(fs_round_digits=digits)
        balances = self._get_account_balances(
            company, date_to=date_to, target_move=target_move, period_mode=False,
            analytic_account_ids=analytic_account_ids
        )

        fy_start = self._get_fiscalyear_start(company, date_to)
        current_year_pl_balances = self._get_account_balances(
            company, date_to=date_to, date_from=fy_start, target_move=target_move,
            period_mode=True, analytic_account_ids=analytic_account_ids
        )
        prior_cutoff = (
                datetime.date.fromisoformat(fy_start) - datetime.timedelta(days=1)
        ).isoformat()
        prior_years_balances = self._get_account_balances(
            company, date_to=prior_cutoff, target_move=target_move, period_mode=False,
            analytic_account_ids=analytic_account_ids
        )

        lines = self._build_balance_sheet_lines(
            balances, company, current_year_pl_balances, prior_years_balances,
            date_to=date_to, fy_start=fy_start, prior_cutoff=prior_cutoff,
        )
        if with_debit_credit:
            dc_map = self._get_account_debit_credit(
                company, date_to=date_to, target_move=target_move, period_mode=False,
                analytic_account_ids=analytic_account_ids
            )
            self._attach_debit_credit(lines, dc_map)
        return {
            "lines": lines,
            "company_name": company.name,
            "currency_name": company.currency_id.name,
            "currency_symbol": company.currency_id.symbol,
            "currency_digits": digits,
            "date_to": date_to,
        }

    @api.model
    def get_profit_and_loss(
            self, date_from, date_to, company_id=None, target_move="posted",
            analytic_account_ids=None, with_debit_credit=False
    ):
        self._check_access()
        if date_from:
            self._parse_date_or_raise(date_from, "date_from")
        if date_to:
            self._parse_date_or_raise(date_to, "date_to")
        company = self._get_company(company_id)
        self = self._scoped_to(company)  # FIX (multi-company)
        # FIX: same currency-precision context as get_balance_sheet().
        digits = company.currency_id.decimal_places if company.currency_id else 2
        self = self.with_context(fs_round_digits=digits)
        balances = self._get_account_balances(
            company, date_from=date_from, date_to=date_to,
            target_move=target_move, period_mode=True,
            analytic_account_ids=analytic_account_ids
        )
        lines = self._build_profit_and_loss_lines(balances, company)
        if with_debit_credit:
            dc_map = self._get_account_debit_credit(
                company, date_from=date_from, date_to=date_to,
                target_move=target_move, period_mode=True,
                analytic_account_ids=analytic_account_ids
            )
            self._attach_debit_credit(lines, dc_map)
        return {
            "lines": lines,
            "company_name": company.name,
            "currency_name": company.currency_id.name,
            "currency_symbol": company.currency_id.symbol,
            "currency_digits": digits,
            "date_from": date_from,
            "date_to": date_to,
        }

    @api.model
    def has_unposted_entries(self, date_from=None, date_to=None, company_id=None):
        """
        FIX: now accepts date_from so P&L can pass a proper period range
        instead of always searching up to date_to only.
        """
        self._check_access()
        company = self._get_company(company_id)
        self = self._scoped_to(company)  # FIX (multi-company)
        if date_to:
            date_to_obj = self._parse_date_or_raise(date_to, "date_to")
        else:
            date_to_obj = datetime.date.today()

        domain = [
            ("company_id", "=", company.id),
            ("state", "=", "draft"),
            ("date", "<=", date_to_obj),
        ]
        if date_from:
            date_from_obj = self._parse_date_or_raise(date_from, "date_from")
            domain.append(("date", ">=", date_from_obj))

        count = self.env["account.move"].search_count(domain)
        return count > 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_company(self, company_id):
        if company_id:
            try:
                cid = int(company_id)
            except (TypeError, ValueError):
                raise ValidationError(_("Invalid company ID: %s") % company_id)
            company = self.env["res.company"].browse(cid)
            # exists() ensures the ID is real and not deleted
            if not company.exists():
                raise ValidationError(_("Company not found: %s") % cid)
            # Enforce multi-company access - must be in user's allowed companies
            # This mirrors controller's check but protects direct engine RPC calls
            allowed_ids = self.env.user.company_ids.ids
            # For sudo/system calls, company_ids may be empty - fall back to env.companies
            if allowed_ids and company.id not in allowed_ids:
                # Also allow if company is the current env.company and user has at least read via record rules
                # but strictest is to deny if not in allowed set
                raise AccessError(_("You do not have access to company '%s' (ID %s).") % (company.display_name, company.id))
            # Extra Odoo record rule check: try to read the record (will raise if no access)
            if hasattr(company, "check_access"):
                company.check_access("read")
            else:  # older Odoo
                company.check_access_rights("read")
                company.check_access_rule("read")
            return company
        # No company_id supplied -> use current env company (already access-checked by Odoo)
        if not self.env.company or not self.env.company.exists():
            raise ValidationError(_("No company found in current environment."))
        return self.env.company

    def _check_access(self):
        """Enforce accounting access - AbstractModel has no ir.model.access check."""
        if not self.env.user.has_group("account.group_account_user"):
            raise AccessError(_("You do not have access to financial reports."))

    def _scoped_to(self, company):
        """Return the engine bound to ``company`` in the ORM environment.

        FIX (multi-company): report queries already filter
        ``company_id = company.id``, but record rules (account.account,
        journals, taxes, analytic accounts) and company-dependent fields
        (account.code in Odoo 19) are evaluated against ``env.companies`` /
        ``env.company``. When the report company is not the user's *active*
        company those lookups silently returned nothing and the report came
        out blank. Access is still enforced by _get_company() beforehand, so
        this never widens what the user may see. Idempotent.
        """
        if self.env.context.get("allowed_company_ids") == [company.id]:
            return self
        return self.with_context(allowed_company_ids=[company.id])

    def _parse_date_or_raise(self, date_str, field_name="date"):
        try:
            return datetime.date.fromisoformat(date_str)
        except Exception:
            raise ValidationError(_("Invalid date format for %s: %s. Expected YYYY-MM-DD.") % (field_name, date_str))

    # ------------------------------------------------------------------
    # FIX (multi-currency correctness): every amount used to be rounded
    # with a hardcoded round(x, 2), regardless of the company's actual
    # currency precision. That's wrong for currencies with 3 decimal
    # places (e.g. Bahraini Dinar, Kuwaiti Dinar, Omani Rial) — a
    # 0.001-unit balance would be silently rounded away.
    #
    # get_balance_sheet() / get_profit_and_loss() / get_tax_report()
    # compute the right precision from company.currency_id.decimal_places
    # once, at the top of each call, and carry it on `self.env.context`
    # (via with_context) so every nested helper below picks it up
    # automatically without needing its signature changed. `_round_digits()`
    # defaults to 2 when no context value is set, which keeps the pure
    # unit tests in test_report_engine_pure.py (which call helpers like
    # _display_asset() directly, without going through those three entry
    # points) working exactly as before.
    # ------------------------------------------------------------------
    def _round_digits(self):
        return self.env.context.get("fs_round_digits", 2)

    def _zero_threshold(self):
        """Half of the smallest representable unit at the current
        precision — used to decide whether a balance is "effectively
        zero" and can be hidden from the report. Was hardcoded to 0.005
        (correct only for 2-decimal currencies)."""
        return 0.5 * (10 ** -self._round_digits())

    def _move_state_domain(self, target_move):
        # FIX (perf): account.move.line.parent_state is a stored, indexed
        # field related to move_id.state. Filtering on it directly avoids
        # an implicit join through account.move on every report query,
        # which matters once the journal has hundreds of thousands of
        # lines. Semantics are identical to the previous move_id.state
        # domain.
        if target_move == "posted":
            return [("parent_state", "=", "posted")]
        if target_move == "draft":
            return [("parent_state", "=", "draft")]
        return [("parent_state", "!=", "cancel")]

    def _get_outstanding_account_ids(self, company):
        journals = self.env["account.journal"].search(
            [("company_id", "=", company.id), ("type", "in", ["bank", "cash"])]
        )
        accounts = (
                journals.mapped("inbound_payment_method_line_ids.payment_account_id")
                | journals.mapped("outbound_payment_method_line_ids.payment_account_id")
        )
        return accounts.ids

    def _get_fiscalyear_start(self, company, date_to):
        date_to_obj = self._parse_date_or_raise(date_to, "date_to")
        try:
            dates = company.compute_fiscalyear_dates(date_to_obj)
            return dates["date_from"].isoformat()
        except Exception:
            return date_to_obj.replace(month=1, day=1).isoformat()

    def _build_analytic_domain(self, analytic_account_ids):
        """Domain restricting ``account.move.line`` to lines that carry ANY of
        the given analytic accounts (percentage-agnostic, multi-plan keys
        "a,b" included).

        Uses the core ``analytic_distribution`` search - no stored helper
        field, so nothing extra is computed/stored on every journal line.

        Rollback switch (kept for the verification period only): set the
        system parameter ``financial_statements_enterprise_view.analytic_filter``
        to ``m2m`` to use the legacy ``analytic_account_ids`` helper again
        (works only while that field still exists).
        """
        if not analytic_account_ids:
            return []
        try:
            ids = [int(i) for i in analytic_account_ids if i]
        except (TypeError, ValueError):
            return []
        if not ids:
            return []

        mode = self.env["ir.config_parameter"].sudo().get_param(
            "financial_statements_enterprise_view.analytic_filter", "distribution")
        use_m2m = (
            mode == "m2m"
            and "analytic_account_ids" in self.env["account.move.line"]._fields
        )
        _logger.debug("Analytic filter (%s) for IDs: %s", "m2m" if use_m2m else "distribution", ids)
        field = "analytic_account_ids" if use_m2m else "analytic_distribution"
        return [(field, "in", ids)]

    def _compute_net_income(self, range_balances, accounts_info):
        income_accs = self._accounts_by_types(
            range_balances, accounts_info, ["income", "income_other"]
        )
        expense_accs = self._accounts_by_types(
            range_balances, accounts_info,
            ["expense_direct_cost", "expense", "expense_depreciation"],
        )
        income_total = self._sum_display(income_accs, self._display_income)
        expense_total = self._sum_display(expense_accs, self._display_expense)
        return round(income_total - expense_total, self._round_digits())

    def _pl_account_ids(self, range_balances, accounts_info):
        income_accs = self._accounts_by_types(
            range_balances, accounts_info, ["income", "income_other"]
        )
        expense_accs = self._accounts_by_types(
            range_balances, accounts_info,
            ["expense_direct_cost", "expense", "expense_depreciation"],
        )
        return [aid for aid, _, _ in income_accs] + [aid for aid, _, _ in expense_accs]

    def _get_account_balances(
            self, company, date_to, target_move="posted", date_from=None,
            period_mode=False, analytic_account_ids=None
    ):
        """Return {account_id: raw_balance} where raw = sum(debit)-sum(credit)."""
        date_to_obj = self._parse_date_or_raise(date_to, "date_to")

        domain = [
                     ("company_id", "=", company.id),
                     ("display_type", "not in", ["line_section", "line_note"]),
                     ("date", "<=", date_to_obj),
                 ] + self._move_state_domain(target_move)

        if period_mode and date_from:
            date_from_obj = self._parse_date_or_raise(date_from, "date_from")
            domain.append(("date", ">=", date_from_obj))

        # FIX: use JSON-safe analytic domain builder
        analytic_domain = self._build_analytic_domain(analytic_account_ids)
        if analytic_domain:
            domain += analytic_domain

        # FIX (Odoo 19): read_group() is deprecated in favor of
        # _read_group(). Same aggregation, different return shape:
        # _read_group() yields plain tuples (one per row) instead of
        # dicts, and a many2one groupby column comes back as a
        # recordset instead of an (id, display_name) tuple.
        groups = self.env["account.move.line"]._read_group(
            domain,
            groupby=["account_id"],
            aggregates=["debit:sum", "credit:sum"],
        )

        result = {}
        for account, debit, credit in groups:
            if not account:
                continue
            result[account.id] = (debit or 0.0) - (credit or 0.0)
        return result

    def _get_account_debit_credit(
            self, company, date_to, target_move="posted", date_from=None,
            period_mode=False, analytic_account_ids=None
    ):
        """Return {account_id: {"debit": x, "credit": y}}."""
        date_to_obj = self._parse_date_or_raise(date_to, "date_to")

        domain = [
                     ("company_id", "=", company.id),
                     ("display_type", "not in", ["line_section", "line_note"]),
                     ("date", "<=", date_to_obj),
                 ] + self._move_state_domain(target_move)

        if period_mode and date_from:
            date_from_obj = self._parse_date_or_raise(date_from, "date_from")
            domain.append(("date", ">=", date_from_obj))

        # FIX: use JSON-safe analytic domain builder
        analytic_domain = self._build_analytic_domain(analytic_account_ids)
        if analytic_domain:
            domain += analytic_domain

        # FIX (Odoo 19): same read_group -> _read_group migration as
        # _get_account_balances above.
        groups = self.env["account.move.line"]._read_group(
            domain,
            groupby=["account_id"],
            aggregates=["debit:sum", "credit:sum"],
        )

        result = {}
        for account, debit, credit in groups:
            if not account:
                continue
            result[account.id] = {
                "debit": debit or 0.0,
                "credit": credit or 0.0,
            }
        return result

    def _attach_debit_credit(self, lines, dc_map):
        total_debit = 0.0
        total_credit = 0.0
        for line in lines:
            if line.get("children"):
                d, c = self._attach_debit_credit(line["children"], dc_map)
            else:
                acc_id = line.get("account_id")
                dc = dc_map.get(acc_id, {}) if acc_id else {}
                d = dc.get("debit") or 0.0
                c = dc.get("credit") or 0.0
            line["debit"] = round(d, self._round_digits())
            line["credit"] = round(c, self._round_digits())
            total_debit += d
            total_credit += c
        return total_debit, total_credit

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
        return round(raw_balance, self._round_digits())

    def _display_liability(self, raw_balance):
        return round(-raw_balance, self._round_digits())

    def _display_income(self, raw_balance):
        return round(-raw_balance, self._round_digits())

    def _display_expense(self, raw_balance):
        return round(raw_balance, self._round_digits())

    def _sum_display(self, items, display_fn):
        return round(sum(display_fn(v) for _, _, v in items), self._round_digits())

    def _account_lines(self, matched, display_fn, parent_key):
        lines = []
        # FIX (analytic columns): an account whose TOTAL is 0 but which has
        # non-zero balances in individual analytic columns (e.g. +22.50 /
        # +225 / -247.50 across warehouses) used to be dropped here, so the
        # section total no longer equalled the sum of its visible rows.
        # main.py passes those account ids through the context.
        force_ids = set(self.env.context.get("fs_force_account_ids") or ())
        for acc_id, info, raw_bal in matched:
            balance = display_fn(raw_bal)
            if abs(balance) < self._zero_threshold() and acc_id not in force_ids:
                continue
            lines.append({
                "id": f"{parent_key}_acc_{acc_id}",
                "name": f"{info.get('code', '')} {info.get('name', '')}".strip(),
                "line_type": "account",
                "style": "account",
                "level": 3,
                "balance": balance,
                "account_id": acc_id,
                "children": [],
            })
        return lines

    def _section_line(self, key, name, balance, style="section", level=0, children=None):
        return {
            "id": key,
            "name": name,
            "line_type": "section",
            "style": style,
            "level": level,
            "balance": round(balance, self._round_digits()),
            "children": children or [],
        }

    def _subtotal_line(self, key, name, balance, level=0):
        return {
            "id": key,
            "name": name,
            "line_type": "subtotal",
            "style": "subtotal",
            "level": level,
            "balance": round(balance, self._round_digits()),
            "children": [],
        }

    def _rollup_balance(self, line):
        if line.get("children"):
            total = sum(self._rollup_balance(child) for child in line["children"])
            line["balance"] = round(total, self._round_digits())
            return line["balance"]
        return line.get("balance") or 0.0

    def _collect_account_ids(self, line):
        """Recursively gather the account ids backing ``line`` and cache
        them on every header/group/subsection row as ``account_ids``.

        Leaf "account" lines already carry a single ``account_id`` and
        "computed" lines (e.g. Current/Previous Year Unallocated Earnings)
        already carry an explicit ``account_ids`` list — both are left
        untouched. For any other row (header/group/subsection) this
        unions the ids of all descendant leaves so that clicking on a
        total like ASSETS, LIABILITIES or EQUITY (& EARNINGS) opens the
        same "Journal Items" drilldown as a single account line, exactly
        like the Enterprise Balance Sheet/P&L. No frontend changes are
        needed: the existing hasDrilldown()/openJournalItems() JS already
        checks for line.account_ids.
        """
        if line.get("account_id"):
            return [line["account_id"]]
        if line.get("account_ids"):
            return list(line["account_ids"])

        ids = []
        for child in line.get("children", []):
            ids.extend(self._collect_account_ids(child))

        if line.get("children"):
            # Preserve order, drop duplicates.
            line["account_ids"] = list(dict.fromkeys(ids))
        return ids

    # ------------------------------------------------------------------
    # Analytic column helpers
    # ------------------------------------------------------------------

    def _flatten_lines(self, lines):
        """Recursively flatten hierarchical lines into {line_id: balance}."""
        result = {}
        for line in lines:
            result[line["id"]] = line.get("balance", 0.0)
            if line.get("children"):
                result.update(self._flatten_lines(line["children"]))
        return result

    def _get_account_balances_batch(self, company, date_to, target_move="posted", date_from=None,
                                     period_mode=False, analytic_account_ids=None):
        """Analytic-weighted balances, aggregated 100% inside PostgreSQL.

        Returns {analytic_id: {account_id: balance}}.
        If analytic_account_ids is falsy, returns {False: balances}.

        Semantics (same as Odoo core):
          * analytic_distribution = {"<id>[,<id>...]": percent}
          * every analytic account inside one key receives the FULL percent
            of that key (a key with two ids = two plans, each at that %).
            The previous Python version divided the percent by the number
            of ids in the key, which under-stated multi-plan lines.

        Performance: one SQL statement per date range, memory O(#accounts x
        #analytics) instead of loading every journal line into Python.
        Record rules are still applied because the row set comes from
        ``_search()``.
        """
        if not analytic_account_ids:
            return {False: self._get_account_balances(
                company, date_to, target_move, date_from, period_mode, None)}
        ids = sorted({int(x) for x in analytic_account_ids if x})
        if not ids:
            return {}

        date_to_obj = self._parse_date_or_raise(date_to, "date_to")
        domain = [
            ("company_id", "=", company.id),
            ("display_type", "not in", ["line_section", "line_note"]),
            ("date", "<=", date_to_obj),
        ] + self._move_state_domain(target_move)
        if period_mode and date_from:
            domain.append(("date", ">=", self._parse_date_or_raise(date_from, "date_from")))

        AML = self.env["account.move.line"]
        # Raw SQL bypasses the ORM cache: push pending writes first.
        AML.flush_model([
            "account_id", "debit", "credit", "analytic_distribution", "date",
            "parent_state", "company_id", "display_type",
        ])
        query = AML._search(domain)  # applies ir.rules / multi-company
        self.env.cr.execute(SQL(
            """
            SELECT aml.account_id,
                   TRIM(a.aid) AS analytic_id,
                   SUM((aml.debit - aml.credit) * d.value::numeric / 100.0)
            FROM account_move_line aml
            CROSS JOIN LATERAL jsonb_each_text(aml.analytic_distribution) AS d(key, value)
            CROSS JOIN LATERAL unnest(string_to_array(d.key, ',')) AS a(aid)
            WHERE aml.id IN %s
              AND aml.analytic_distribution IS NOT NULL
              AND TRIM(a.aid) = ANY(%s)
            GROUP BY aml.account_id, TRIM(a.aid)
            """,
            query.subselect(),
            [str(i) for i in ids],
        ))
        result = {aid: {} for aid in ids}
        for account_id, analytic_id, balance in self.env.cr.fetchall():
            result[int(analytic_id)][account_id] = float(balance or 0.0)
        return result

    def _get_unassigned_balances(
            self, company, date_to, target_move="posted", date_from=None,
            period_mode=False
    ):
        """Balances of the part of every journal line NOT covered by an
        analytic distribution -> {account_id: balance}.

        Per line: unassigned share = 100 - SUM(all distribution percents),
        floored at 0. No distribution = 100% unassigned; 60/40 = 0%;
        60% only = 40%. All keys are summed because each key is one
        allocation slice of the line ("a,b" is one slice shared by two
        plans, not two slices).

        Guarantees  sum(analytic columns) + Unassigned == Total  for
        single-plan setups. One SQL statement; record rules applied via
        ``_search()`` exactly like _get_account_balances_batch().
        """
        date_to_obj = self._parse_date_or_raise(date_to, "date_to")
        domain = [
            ("company_id", "=", company.id),
            ("display_type", "not in", ["line_section", "line_note"]),
            ("date", "<=", date_to_obj),
        ] + self._move_state_domain(target_move)
        if period_mode and date_from:
            domain.append(("date", ">=", self._parse_date_or_raise(date_from, "date_from")))

        AML = self.env["account.move.line"]
        AML.flush_model([
            "account_id", "debit", "credit", "analytic_distribution", "date",
            "parent_state", "company_id", "display_type",
        ])
        query = AML._search(domain)
        self.env.cr.execute(SQL(
            """
            SELECT aml.account_id,
                   SUM((aml.debit - aml.credit)
                       * GREATEST(0, 100 - COALESCE(s.pct, 0)) / 100.0)
            FROM account_move_line aml
            LEFT JOIN LATERAL (
                SELECT SUM(d.value::numeric) AS pct
                FROM jsonb_each_text(
                    CASE WHEN jsonb_typeof(aml.analytic_distribution) = 'object'
                         THEN aml.analytic_distribution
                         ELSE '{}'::jsonb END
                ) AS d(key, value)
            ) s ON TRUE
            WHERE aml.id IN %s
            GROUP BY aml.account_id
            """,
            query.subselect(),
        ))
        return {
            account_id: float(balance or 0.0)
            for account_id, balance in self.env.cr.fetchall()
        }

    @api.model
    def get_analytic_report(
            self, report_type, date_from, date_to, company_id=None,
            target_move="posted", analytic_account_ids=None,
            include_unassigned=False,
    ):
        """Balance Sheet / P&L with one column per analytic account, an
        optional "Unassigned" column and a company-wide "Total" column.

        Lives in the engine (not the controller) so it is unit-testable
        without an HTTP request. Cost: one SQL aggregation per date range
        (3 for BS, 1 for P&L) for the analytic columns, plus the same
        again for the Unassigned column when requested.
        """
        self._check_access()
        company = self._get_company(company_id)
        self = self._scoped_to(company)  # FIX (multi-company)
        is_bs = report_type == "bs"
        ids = sorted({int(i) for i in (analytic_account_ids or []) if i})
        digits = company.currency_id.decimal_places if company.currency_id else 2
        if not is_bs and not date_from:
            date_from = datetime.date.today().replace(month=1, day=1).isoformat()

        if is_bs:
            fy_start = self._get_fiscalyear_start(company, date_to)
            prior_cutoff = (
                datetime.date.fromisoformat(fy_start) - datetime.timedelta(days=1)
            ).isoformat()
            specs = {
                "bal": {"date_to": date_to, "period_mode": False},
                "cur": {"date_to": date_to, "date_from": fy_start, "period_mode": True},
                "prior": {"date_to": prior_cutoff, "period_mode": False},
            }
        else:
            specs = {"cur": {"date_to": date_to, "date_from": date_from, "period_mode": True}}

        unassigned_key = "unassigned"
        batches = {}
        for key, kw in specs.items():
            per_analytic = (
                self._get_account_balances_batch(
                    company, target_move=target_move, analytic_account_ids=ids, **kw)
                if ids else {}
            )
            if include_unassigned:
                per_analytic = dict(per_analytic)
                per_analytic[unassigned_key] = self._get_unassigned_balances(
                    company, target_move=target_move, **kw)
            batches[key] = per_analytic

        # Accounts with a balance in ANY column must stay visible even if
        # their grand total nets to zero (else section != sum(children)).
        force = set()
        for per_analytic_maps in batches.values():
            for acc_map in per_analytic_maps.values():
                force.update(a for a, v in acc_map.items() if abs(v) > 1e-9)

        eng = self.with_context(
            fs_round_digits=digits, fs_force_account_ids=tuple(sorted(force)))

        if is_bs:
            result = eng.get_balance_sheet(
                date_to=date_to, company_id=company.id, target_move=target_move,
                analytic_account_ids=None)
        else:
            result = eng.get_profit_and_loss(
                date_from=date_from, date_to=date_to, company_id=company.id,
                target_move=target_move, analytic_account_ids=None)

        column_keys = list(ids) + ([unassigned_key] if include_unassigned else [])
        analytic_maps = {}
        for aid in column_keys:
            if is_bs:
                alines = eng._build_balance_sheet_lines(
                    batches["bal"].get(aid, {}), company,
                    batches["cur"].get(aid, {}), batches["prior"].get(aid, {}),
                    date_to=date_to, fy_start=fy_start, prior_cutoff=prior_cutoff)
            else:
                alines = eng._build_profit_and_loss_lines(
                    batches["cur"].get(aid, {}), company)
            analytic_maps[aid] = eng._flatten_lines(alines)

        total_map = eng._flatten_lines(result["lines"])
        eng._attach_analytic_balances(result["lines"], analytic_maps, total_map)

        accounts = self.env["account.analytic.account"].browse(ids).exists()
        columns = [{"id": acc.id, "name": acc.name} for acc in accounts]
        if include_unassigned:
            columns.append({"id": unassigned_key, "name": _("Unassigned")})
        columns.append({"id": "total", "name": _("Total")})
        result["analytic_columns"] = columns
        result["has_unposted"] = self.has_unposted_entries(
            date_from=date_from if not is_bs else None,
            date_to=date_to, company_id=company.id)
        result["report_type"] = report_type
        return result

    def _attach_analytic_balances(self, lines, analytic_maps, total_map):
        """Attach analytic_balances dict to each line for multi-column rendering.

        Args:
            lines: the main report lines (hierarchical)
            analytic_maps: {analytic_account_id: {line_id: balance}}
            total_map: {line_id: balance} for the Total column (no analytic filter)
        """
        for line in lines:
            line_id = line["id"]
            analytic_balances = {}
            for acc_id, acc_map in analytic_maps.items():
                analytic_balances[acc_id] = acc_map.get(line_id, 0.0)
                # Also support string key for frontend JSON coercion
                analytic_balances[str(acc_id)] = acc_map.get(line_id, 0.0)
            analytic_balances["total"] = total_map.get(line_id, 0.0)
            line["analytic_balances"] = analytic_balances
            if line.get("children"):
                self._attach_analytic_balances(line["children"], analytic_maps, total_map)

    # ------------------------------------------------------------------
    # Balance Sheet
    # ------------------------------------------------------------------

    def _build_balance_sheet_lines(
            self, balances, company, current_year_pl_balances=None,
            prior_years_balances=None, date_to=None, fy_start=None, prior_cutoff=None,
    ):
        account_ids = (
                set(balances.keys())
                | set((current_year_pl_balances or {}).keys())
                | set((prior_years_balances or {}).keys())
        )
        accounts_info = self._load_accounts_info(account_ids)
        outstanding_ids = self._get_outstanding_account_ids(company)

        # --- ASSETS ---
        bank_cash = self._accounts_by_types(
            balances, accounts_info, ["asset_cash"], exclude_ids=outstanding_ids
        )
        outstanding = [
            (aid, info, bal)
            for aid, info, bal in self._accounts_by_types(
                balances, accounts_info,
                ["asset_cash", "asset_current", "asset_receivable"],
            )
            if aid in outstanding_ids
        ]
        outstanding_asset_ids = {aid for aid, _info, _bal in outstanding}

        receivables = self._accounts_by_types(
            balances, accounts_info, ["asset_receivable"], exclude_ids=outstanding_ids
        )
        prepayments = self._accounts_by_types(
            balances, accounts_info, ["asset_prepayments"]
        )
        other_current = self._accounts_by_types(
            balances, accounts_info, ["asset_current"], exclude_ids=outstanding_ids
        )

        bank_section = self._section_line(
            "bank_cash", "Bank and Cash",
            self._sum_display(bank_cash + outstanding, self._display_asset),
            style="subsection", level=2,
            children=self._account_lines(bank_cash + outstanding, self._display_asset, "bank_cash"),
        )
        recv_section = self._section_line(
            "receivables", "Receivables",
            self._sum_display(receivables, self._display_asset),
            style="subsection", level=2,
            children=self._account_lines(receivables, self._display_asset, "recv"),
        )
        prep_section = self._section_line(
            "prepayments", "Prepayments",
            self._sum_display(prepayments, self._display_asset),
            style="subsection", level=2,
            children=self._account_lines(prepayments, self._display_asset, "prep"),
        )
        other_current_section = self._section_line(
            "other_current_assets", "Other Current Assets",
            self._sum_display(other_current, self._display_asset),
            style="subsection", level=2,
            children=self._account_lines(other_current, self._display_asset, "other_ca"),
        )

        current_assets = self._section_line(
            "current_assets", "Current Assets", 0, style="group", level=1,
            children=[
                s for s in [bank_section, recv_section, prep_section, other_current_section]
                if s["balance"] or s["children"]
            ],
        )
        self._rollup_balance(current_assets)

        fixed = self._accounts_by_types(balances, accounts_info, ["asset_fixed"])
        fixed_section = self._section_line(
            "fixed_assets", "Fixed Assets",
            self._sum_display(fixed, self._display_asset),
            style="group", level=1,
            children=self._account_lines(fixed, self._display_asset, "fixed"),
        )

        non_current = self._accounts_by_types(balances, accounts_info, ["asset_non_current"])
        non_current_section = self._section_line(
            "non_current_assets", "Non-current Assets",
            self._sum_display(non_current, self._display_asset),
            style="group", level=1,
            children=self._account_lines(non_current, self._display_asset, "nca"),
        )

        assets = self._section_line(
            "assets", "ASSETS", 0, style="header", level=0,
            children=[
                s for s in [current_assets, fixed_section, non_current_section]
                if s["balance"] or s["children"]
            ],
        )
        self._rollup_balance(assets)
        self._collect_account_ids(assets)

        # --- LIABILITIES ---
        credit_card = self._accounts_by_types(
            balances, accounts_info, ["liability_credit_card"]
        )
        payables = self._accounts_by_types(
            balances, accounts_info, ["liability_payable"],
            exclude_ids=outstanding_asset_ids,
        )
        other_current_liab = self._accounts_by_types(
            balances, accounts_info, ["liability_current"],
            exclude_ids=outstanding_asset_ids,
        )

        cc_section = self._section_line(
            "credit_card", "Credit Card",
            self._sum_display(credit_card, self._display_liability),
            style="subsection", level=2,
            children=self._account_lines(credit_card, self._display_liability, "cc"),
        )
        pay_section = self._section_line(
            "payables", "Payables",
            self._sum_display(payables, self._display_liability),
            style="subsection", level=2,
            children=self._account_lines(payables, self._display_liability, "pay"),
        )
        ocl_section = self._section_line(
            "other_current_liab", "Other Current Liabilities",
            self._sum_display(other_current_liab, self._display_liability),
            style="subsection", level=2,
            children=self._account_lines(other_current_liab, self._display_liability, "ocl"),
        )

        current_liabilities = self._section_line(
            "current_liabilities", "Current Liabilities", 0, style="group", level=1,
            children=[
                s for s in [cc_section, pay_section, ocl_section]
                if s["balance"] or s["children"]
            ],
        )
        self._rollup_balance(current_liabilities)

        non_current_liab = self._accounts_by_types(
            balances, accounts_info, ["liability_non_current"]
        )
        non_current_liab_section = self._section_line(
            "non_current_liabilities", "Non-current Liabilities",
            self._sum_display(non_current_liab, self._display_liability),
            style="group", level=1,
            children=self._account_lines(non_current_liab, self._display_liability, "ncl"),
        )

        liabilities = self._section_line(
            "liabilities", "LIABILITIES", 0, style="header", level=0,
            children=[
                s for s in [current_liabilities, non_current_liab_section]
                if s["balance"] or s["children"]
            ],
        )
        self._rollup_balance(liabilities)
        self._collect_account_ids(liabilities)

        # --- EQUITY ---
        equity_accounts = self._accounts_by_types(balances, accounts_info, ["equity"])
        unaffected = self._accounts_by_types(balances, accounts_info, ["equity_unaffected"])

        # FIX (retained detection): use word-boundary matching, not plain substring.
        # Old `kw in haystack` flagged any equity account containing "أرباح" anywhere (e.g. "أرباح توزيعات")
        # as retained. Now uses regex \b boundaries and separates Arabic tokens properly.
        import re
        _RETAINED_KEYWORDS = (
            "retained", "previous", "brought forward", "b/f", "b/fwd",
            "report à nouveau", "gewinnvortrag", "utili portati",
            "أرباح مبقاة", "أرباح محتجزة", "ارباح مبقاة", "ارباح محتجزة",
            "مرحلة", "مدورة", "مرحل", "مبقاة",
        )

        def _is_retained(info):
            name = (info.get("name") or "").lower()
            code = (info.get("code") or "").lower()
            haystack = f"{name} {code}"
            # Normalize spaces and punctuation for Arabic
            for kw in _RETAINED_KEYWORDS:
                # For multi-word keywords require exact phrase, for single words require word boundary
                pattern = r"\b" + re.escape(kw) + r"\b"
                if re.search(pattern, haystack):
                    return True
            return False

        prev_year_accs = [
            (aid, info, bal)
            for aid, info, bal in equity_accounts
            if _is_retained(info)
        ]
        prev_year_ids = {aid for aid, _, _ in prev_year_accs}
        regular_equity_accs = [
            (aid, info, bal)
            for aid, info, bal in equity_accounts
            if aid not in prev_year_ids
        ]

        equity_section = self._section_line(
            "equity", "Equity",
            self._sum_display(regular_equity_accs, self._display_liability),
            style="group", level=1,
            children=self._account_lines(regular_equity_accs, self._display_liability, "eq"),
        )

        current_year_pl_net = self._compute_net_income(
            current_year_pl_balances or {}, accounts_info
        )
        prior_years_pl_net = self._compute_net_income(
            prior_years_balances or {}, accounts_info
        )

        # FIX: equity_unaffected belongs to Previous Years, not Current Year. Auditor split now correct.
        current_year_bal = round(
            current_year_pl_net,
            self._round_digits(),
        )
        current_year = self._section_line(
            "current_year_earnings", "Current Year Unallocated Earnings",
            current_year_bal, style="account", level=2, children=[],
        )
        current_year["line_type"] = "computed"
        current_year["account_ids"] = self._pl_account_ids(current_year_pl_balances or {}, accounts_info)
        current_year["date_from"] = fy_start
        current_year["date_to"] = date_to

        prev_year_balance = round(
            self._sum_display(prev_year_accs, self._display_liability)
            + self._sum_display(unaffected, self._display_liability)
            + prior_years_pl_net,
            self._round_digits(),
        )
        prev_year = self._section_line(
            "previous_years_earnings", "Previous Years Earnings",
            prev_year_balance, style="account", level=2, children=[],
        )
        prev_year["line_type"] = "computed"
        prev_year["account_ids"] = (
                [aid for aid, _, _ in prev_year_accs]
                + [aid for aid, _, _ in unaffected]
                + self._pl_account_ids(prior_years_balances or {}, accounts_info)
        )
        prev_year["date_from"] = None
        prev_year["date_to"] = prior_cutoff

        earnings = self._section_line(
            "earnings", "Earnings", 0, style="group", level=1,
            children=[current_year, prev_year],
        )
        self._rollup_balance(earnings)

        equity = self._section_line(
            "equity_section", "EQUITY (& EARNINGS)", 0, style="header", level=0,
            children=[
                s for s in [equity_section, earnings]
                if s["balance"] or s["children"]
            ],
        )
        self._rollup_balance(equity)
        self._collect_account_ids(equity)

        liab_equity_total = self._subtotal_line(
            "liabilities_equity", "LIABILITIES + EQUITY",
            liabilities["balance"] + equity["balance"], level=0,
        )
        # LIABILITIES + EQUITY has no children of its own (it's a sum of
        # two sibling headers), so its drilldown set is built explicitly
        # from the two headers it totals.
        liab_equity_total["account_ids"] = list(dict.fromkeys(
            liabilities.get("account_ids", []) + equity.get("account_ids", [])
        ))

        return [assets, liabilities, equity, liab_equity_total]

    # ------------------------------------------------------------------
    # Profit & Loss
    # ------------------------------------------------------------------

    def _build_profit_and_loss_lines(self, balances, company):
        account_ids = set(balances.keys())
        accounts_info = self._load_accounts_info(account_ids)

        revenue_accs = self._accounts_by_types(balances, accounts_info, ["income"])
        cor_accs = self._accounts_by_types(balances, accounts_info, ["expense_direct_cost"])
        opex_accs = self._accounts_by_types(
            balances, accounts_info, ["expense", "expense_depreciation"]
        )
        other_income_accs = self._accounts_by_types(balances, accounts_info, ["income_other"])
        allocation_accs = self._accounts_by_types(balances, accounts_info, ["equity"])

        revenue_total = self._sum_display(revenue_accs, self._display_income)
        cor_total = self._sum_display(cor_accs, self._display_expense)
        opex_total = self._sum_display(opex_accs, self._display_expense)

        # Plain account-id lists per bucket. Used below to give every
        # header/subtotal row an explicit ``account_ids`` so it becomes
        # drillable into journal items — same mechanism as the Balance
        # Sheet fix. Built by hand (rather than via a generic recursive
        # collector) because "Revenue" visually nests "Costs of Revenue"
        # as a child row without including it in Revenue's own total, so
        # a naive recursive union would wrongly pull COGS accounts into
        # the Revenue drilldown.
        revenue_ids = [aid for aid, _, _ in revenue_accs]
        cor_ids = [aid for aid, _, _ in cor_accs]
        opex_ids = [aid for aid, _, _ in opex_accs]
        other_income_ids = [aid for aid, _, _ in other_income_accs]
        alloc_ids = [aid for aid, _, _ in allocation_accs]

        def _dedup(*id_lists):
            merged = []
            for ids in id_lists:
                merged.extend(ids)
            return list(dict.fromkeys(merged))

        revenue_children = self._account_lines(revenue_accs, self._display_income, "rev")
        cor_line = self._section_line(
            "cost_of_revenue", "Costs of Revenue", cor_total,
            style="subsection", level=1,
            children=self._account_lines(cor_accs, self._display_expense, "cor"),
        )
        cor_line["account_ids"] = cor_ids
        if cor_total or cor_line["children"]:
            revenue_children.append(cor_line)

        revenue = self._section_line(
            "revenue", "Revenue", revenue_total, style="group", level=0,
            children=revenue_children,
        )
        revenue["account_ids"] = revenue_ids
        gross_profit = self._subtotal_line(
            "gross_profit", "Gross Profit", revenue_total - cor_total, level=0
        )
        gross_profit["account_ids"] = _dedup(revenue_ids, cor_ids)
        opex = self._section_line(
            "operating_expenses", "Operating Expenses", opex_total,
            style="group", level=0,
            children=self._account_lines(opex_accs, self._display_expense, "opex"),
        )
        opex["account_ids"] = opex_ids
        operating_income = self._subtotal_line(
            "operating_income", "Operating Income (or Loss)",
            gross_profit["balance"] - opex_total, level=0,
        )
        operating_income["account_ids"] = _dedup(gross_profit["account_ids"], opex_ids)

        other_income_total = self._sum_display(other_income_accs, self._display_income)
        other_income = self._section_line(
            "other_income", "Other Income", other_income_total,
            style="group", level=0,
            children=self._account_lines(other_income_accs, self._display_income, "oi"),
        )
        other_income["account_ids"] = other_income_ids
        other_expense = self._section_line(
            "other_expenses", "Other Expenses", 0, style="group", level=0, children=[],
        )
        # No accounts are modeled for this bucket yet, so it stays
        # non-drillable (empty account_ids) exactly like today.
        other_expense["account_ids"] = []
        net_profit = self._subtotal_line(
            "net_profit", "Net Profit",
            operating_income["balance"] + other_income_total - other_expense["balance"],
            level=0,
        )
        net_profit["account_ids"] = _dedup(
            operating_income["account_ids"], other_income_ids, other_expense["account_ids"]
        )

        alloc_total = self._sum_display(allocation_accs, self._display_expense)
        allocations = self._section_line(
            "allocations", "Allocations and Withdrawals", alloc_total,
            style="group", level=0,
            children=self._account_lines(allocation_accs, self._display_expense, "alloc"),
        )
        allocations["account_ids"] = alloc_ids
        net_after_alloc = self._subtotal_line(
            "net_after_alloc", "Net Profit Left After Allocations and Withdrawals",
            net_profit["balance"] - alloc_total, level=0,
        )
        net_after_alloc["account_ids"] = _dedup(net_profit["account_ids"], alloc_ids)

        return [
            revenue, gross_profit, opex, operating_income,
            other_income, other_expense, net_profit, allocations, net_after_alloc,
        ]

    # ------------------------------------------------------------------
    # Tax Report (VAT Return — Saudi Arabia)
    # ------------------------------------------------------------------

    # Report line definitions: (box number, line_key, section, name, show_vat).
    # Box numbers match the 'N(B)' / 'N(T)' Tax Grid naming convention
    # used by Settings > Taxes > Tax Grids and by the native Odoo Tax
    # Report (e.g. the reverse charge tax's base grid is '9(B)', its VAT
    # grid is '9(T)').
    _VAT_GRID_LINES = [
        (1, "std_sales", "sales", "Standard rated sales", True),
        (2, "reduced_sales", "sales",
         "Private Healthcare / Private Education / First house sales to citizens", True),
        (3, "zero_sales", "sales", "Zero rated domestic sales", False),
        (4, "exports", "sales", "Exports", False),
        (5, "exempt_sales", "sales", "Exempt sales", False),
        (7, "std_purch", "purchases", "Standard rated domestic purchases", True),
        (8, "import_customs", "purchases",
         "Imports subject to VAT paid at customs", True),
        (9, "import_rc", "purchases",
         "Imports subject to VAT accounted for through reverse charge mechanism", True),
        (10, "zero_purch", "purchases", "Zero rated purchases", False),
        (11, "exempt_purch", "purchases", "Exempt purchases", False),
    ]

    def _get_vat_grid_tags(self):
        """Look up the Enterprise-style 'N(B)'/'N(T)' tax grid tags.

        These are the same account.account.tag records (applicability =
        'taxes') that the native Odoo Tax Report reads when a tax's
        repartition line has a Tax Grid assigned in Settings > Taxes.
        Returns {tag_name: tag_id}. Empty if the company has none of
        these tags defined, in which case the caller falls back to the
        legacy name-based bucketing.
        """
        tag_names = []
        for number, key, section, name, show_vat in self._VAT_GRID_LINES:
            tag_names.append("%s(B)" % number)
            if show_vat:
                tag_names.append("%s(T)" % number)
        tags = self.env["account.account.tag"].search_read(
            [("applicability", "=", "taxes"), ("name", "in", tag_names)],
            ["id", "name"],
        )
        return {t["name"]: t["id"] for t in tags}

    def _company_uses_vat_grid_tags(self, company, tag_id_by_name):
        """True only if THIS company's own taxes reference at least one
        of the given grid tags on their repartition lines.

        account.account.tag has no company_id, so a naive "do any of
        these tags exist" check (the old behavior) leaks across
        companies: Company A configuring proper Tax Grids would silently
        flip Company B onto the grid-based path too, even though
        Company B's taxes were never tagged — producing an all-zero VAT
        return for Company B despite real transactions. This scopes the
        check to the company's own account.tax repartition lines.
        """
        if not tag_id_by_name:
            return False
        tag_ids = set(tag_id_by_name.values())
        taxes = self.env["account.tax"].search([("company_id", "=", company.id)])
        if not taxes:
            return False
        rep_lines = (
            taxes.mapped("invoice_repartition_line_ids")
            | taxes.mapped("refund_repartition_line_ids")
        )
        company_tag_ids = set(rep_lines.mapped("tag_ids").ids)
        return bool(company_tag_ids & tag_ids)

    def _get_tax_report_buckets_by_grid(self, base_domain, tag_id_by_name):
        """Aggregate base/VAT amounts per report line using Tax Grid tags.

        FIX (perf): previously loaded every matching move line via
        search_read (could be 100k+ lines per quarter -> OOM / timeout).
        Now aggregates per tag with _read_group so only ~20 small
        aggregation queries are executed regardless of data volume.
        """
        buckets = {}
        for number, key, section, name, show_vat in self._VAT_GRID_LINES:
            base_tag = "%s(B)" % number
            vat_tag = "%s(T)" % number if show_vat else None
            base_tag_id = tag_id_by_name.get(base_tag)
            vat_tag_id = tag_id_by_name.get(vat_tag) if vat_tag else None

            base_amount = 0.0
            base_tax_ids = set()
            if base_tag_id:
                # Amount: single _read_group without groupby
                res = self.env["account.move.line"]._read_group(
                    base_domain + [("tax_tag_ids", "=", base_tag_id)],
                    aggregates=["credit:sum", "debit:sum"],
                )
                if res:
                    # res[0] = (credit_sum, debit_sum) in aggregate order
                    try:
                        credit_sum, debit_sum = res[0][0] or 0.0, res[0][1] or 0.0
                    except Exception:
                        credit_sum = debit_sum = 0.0
                    base_amount = abs((credit_sum or 0.0) - (debit_sum or 0.0))
                # Distinct taxes contributing to this base tag
                # groupby Many2many yields one row per tax
                try:
                    tax_groups = self.env["account.move.line"]._read_group(
                        base_domain + [("tax_tag_ids", "=", base_tag_id), ("tax_ids", "!=", False)],
                        groupby=["tax_ids"],
                        aggregates=["credit:sum"],
                    )
                    for grp in tax_groups:
                        tax_rec = grp[0] if grp else None
                        if tax_rec:
                            try:
                                base_tax_ids.update(tax_rec.ids)
                            except Exception:
                                if getattr(tax_rec, "id", None):
                                    base_tax_ids.add(tax_rec.id)
                except Exception:
                    _logger.debug("Failed to collect base tax_ids for tag %s", base_tag)

            vat_amount = 0.0
            vat_tax_ids = set()
            if show_vat and vat_tag_id:
                res = self.env["account.move.line"]._read_group(
                    base_domain + [("tax_tag_ids", "=", vat_tag_id)],
                    aggregates=["credit:sum", "debit:sum"],
                )
                if res:
                    try:
                        credit_sum, debit_sum = res[0][0] or 0.0, res[0][1] or 0.0
                    except Exception:
                        credit_sum = debit_sum = 0.0
                    vat_amount = abs((credit_sum or 0.0) - (debit_sum or 0.0))
                # VAT lines carry tax_line_id (not tax_ids)
                try:
                    vat_groups = self.env["account.move.line"]._read_group(
                        base_domain + [("tax_tag_ids", "=", vat_tag_id), ("tax_line_id", "!=", False)],
                        groupby=["tax_line_id"],
                        aggregates=["credit:sum"],
                    )
                    for grp in vat_groups:
                        tax_rec = grp[0] if grp else None
                        if tax_rec:
                            try:
                                vat_tax_ids.update(tax_rec.ids)
                            except Exception:
                                if getattr(tax_rec, "id", None):
                                    vat_tax_ids.add(tax_rec.id)
                except Exception:
                    _logger.debug("Failed to collect vat tax_ids for tag %s", vat_tag)
                # Some base lines also carry VAT tag via repartition? include tax_ids too
                try:
                    extra_groups = self.env["account.move.line"]._read_group(
                        base_domain + [("tax_tag_ids", "=", vat_tag_id), ("tax_ids", "!=", False)],
                        groupby=["tax_ids"],
                        aggregates=["credit:sum"],
                    )
                    for grp in extra_groups:
                        tax_rec = grp[0] if grp else None
                        if tax_rec:
                            try:
                                vat_tax_ids.update(tax_rec.ids)
                            except Exception:
                                pass
                except Exception:
                    pass

            tax_ids = base_tax_ids | vat_tax_ids if show_vat else base_tax_ids
            buckets[key] = {"base": base_amount, "vat": vat_amount if show_vat else 0.0, "tax_ids": list(tax_ids)}
        return buckets

    def _get_tax_report_buckets_by_name(self, base_domain):
        """Legacy fallback: infer each tax's report bucket from keywords
        in its name. Only used when the company has no 'N(B)'/'N(T)' tax
        grid tags configured at all. Still guards against
        repartition-line cancellation (e.g. reverse charge taxes) by
        only summing the positive-factor repartition line of each tax.
        """
        # FIX (Odoo 19): read_group(..., lazy=False) -> _read_group().
        # _read_group() is always "flat" (no lazy mode), so the
        # lazy=False argument simply goes away. Each groupby column
        # (tax_line_id, tax_repartition_line_id) comes back as a
        # recordset instead of an (id, display_name) tuple / False.
        tax_line_domain = base_domain + [("tax_line_id", "!=", False)]
        tax_line_groups = self.env["account.move.line"]._read_group(
            tax_line_domain,
            groupby=["tax_line_id", "tax_repartition_line_id"],
            aggregates=["credit:sum", "debit:sum"],
        )

        rep_line_ids = {
            rep_line.id
            for _tax_line, rep_line, _credit, _debit in tax_line_groups
            if rep_line
        }
        rep_line_factors = {}
        if rep_line_ids:
            rep_lines = self.env["account.tax.repartition.line"].search_read(
                [("id", "in", list(rep_line_ids))], ["id", "factor_percent"],
            )
            rep_line_factors = {r["id"]: r["factor_percent"] for r in rep_lines}

        tax_vat_amounts = {}
        for tax_line, rep_line, credit, debit in tax_line_groups:
            if not tax_line:
                continue
            tid = tax_line.id
            rep_id = rep_line.id if rep_line else False
            # Skip the negative/offsetting repartition line so reverse
            # charge (and any other multi-repartition-line) taxes don't
            # net to zero.
            if rep_id and rep_line_factors.get(rep_id, 100) < 0:
                continue
            tax_vat_amounts[tid] = tax_vat_amounts.get(tid, 0.0) + (
                (credit or 0.0) - (debit or 0.0)
            )

        # FIX (perf): previously loaded every base line via search_read.
        # Now one _read_group per tax -> O(num_taxes) not O(num_lines).
        base_line_domain = base_domain + [("tax_ids", "!=", False)]
        tax_base_amounts = {}
        try:
            base_groups = self.env["account.move.line"]._read_group(
                base_line_domain,
                groupby=["tax_ids"],
                aggregates=["credit:sum", "debit:sum"],
            )
            for grp in base_groups:
                # grp = (tax_ids_recordset, credit_sum, debit_sum)
                tax_rec, credit_sum, debit_sum = grp[0], grp[1], grp[2]
                if not tax_rec:
                    continue
                net = (credit_sum or 0.0) - (debit_sum or 0.0)
                # Many2many groupby yields one row per tax; but if a line
                # carries multiple taxes it is counted in each group's sum
                # via the SQL join — same semantics as the old Python loop.
                for tax in tax_rec:
                    tax_base_amounts[tax.id] = tax_base_amounts.get(tax.id, 0.0) + net
        except Exception as e:
            _logger.warning("Fallback to search_read for tax base amounts: %s", e)
            base_line_recs = self.env["account.move.line"].search_read(
                base_line_domain, ["tax_ids", "credit", "debit"],
            )
            for rec in base_line_recs:
                net = (rec.get("credit") or 0.0) - (rec.get("debit") or 0.0)
                for tid in (rec.get("tax_ids") or []):
                    tax_base_amounts[tid] = tax_base_amounts.get(tid, 0.0) + net

        all_tax_ids = set(tax_vat_amounts.keys()) | set(tax_base_amounts.keys())
        taxes_info = {}
        if all_tax_ids:
            taxes = self.env["account.tax"].search_read(
                [("id", "in", list(all_tax_ids))],
                ["id", "name", "type_tax_use", "amount", "amount_type"],
            )
            taxes_info = {t["id"]: t for t in taxes}

        buckets = {
            key: {"base": 0.0, "vat": 0.0, "tax_ids": []}
            for _, key, _, _, _ in self._VAT_GRID_LINES
        }

        for tid, tinfo in taxes_info.items():
            use = tinfo.get("type_tax_use", "")
            amount = tinfo.get("amount") or 0.0
            amount_type = tinfo.get("amount_type", "percent")
            name_lower = (tinfo.get("name") or "").lower()
            base = tax_base_amounts.get(tid, 0.0)
            vat = tax_vat_amounts.get(tid, 0.0)
            key = None

            if use == "sale":
                if amount == 0.0:
                    if "export" in name_lower:
                        key = "exports"
                    elif any(k in name_lower for k in
                             ["healthcare", "education", "first house", "citizen"]):
                        key = "reduced_sales"
                    elif amount_type == "fixed" or "exempt" in name_lower:
                        key = "exempt_sales"
                    else:
                        key = "zero_sales"
                elif 0 < amount <= 6:
                    key = "reduced_sales"
                else:
                    key = "std_sales"
            elif use == "purchase":
                if amount == 0.0:
                    key = "exempt_purch" if "exempt" in name_lower else "zero_purch"
                elif "reverse" in name_lower:
                    key = "import_rc"
                elif "import" in name_lower or "custom" in name_lower:
                    key = "import_customs"
                else:
                    key = "std_purch"

            if key is None:
                continue

            buckets[key]["base"] += abs(base)
            if key not in ("zero_sales", "exports", "exempt_sales",
                           "zero_purch", "exempt_purch"):
                buckets[key]["vat"] += abs(vat)
            buckets[key]["tax_ids"].append(tid)

        return buckets

    @api.model
    def get_tax_report(
            self, date_from, date_to, company_id=None,
            target_move="posted", analytic_account_ids=None
    ):
        self._check_access()
        if date_from:
            self._parse_date_or_raise(date_from, "date_from")
        if date_to:
            self._parse_date_or_raise(date_to, "date_to")
        company = self._get_company(company_id)
        self = self._scoped_to(company)  # FIX (multi-company)
        # FIX: same currency-precision context as get_balance_sheet().
        digits = company.currency_id.decimal_places if company.currency_id else 2
        self = self.with_context(fs_round_digits=digits)

        date_from_obj = self._parse_date_or_raise(date_from, "date_from") if date_from else datetime.date.today().replace(month=1, day=1)
        date_to_obj = self._parse_date_or_raise(date_to, "date_to") if date_to else datetime.date.today()

        move_state_domain = self._move_state_domain(target_move)
        base_domain = [
                          ("company_id", "=", company.id),
                          ("display_type", "not in", ["line_section", "line_note"]),
                          ("date", ">=", date_from_obj),
                          ("date", "<=", date_to_obj),
                      ] + move_state_domain

        # FIX: use JSON-safe analytic domain builder
        analytic_domain = self._build_analytic_domain(analytic_account_ids)
        if analytic_domain:
            base_domain += analytic_domain

        # FIX: bucket each tax by its Tax Grid (account.account.tag, e.g.
        # '9(B)'/'9(T)') exactly like Settings > Taxes > Tax Grids and the
        # native Odoo Tax Report do, instead of guessing the bucket from
        # the tax's name. This means: create a new tax, assign the
        # correct grid in the UI, and both this report and the native
        # one update together — no code change needed. Falls back to
        # legacy name-based matching only if the company has no grid
        # tags configured at all.
        #
        # FIX (multi-company correctness): account.account.tag is NOT
        # company-scoped (it's shared config data). _get_vat_grid_tags()
        # therefore used to return truthy results as soon as *any*
        # company in the database had grid tags configured — even if
        # *this* company's own taxes never reference them. That silently
        # switched this company onto the grid-based path, which then
        # matched zero move lines (its taxes carry no such tags) and
        # returned an all-zero VAT return despite real, posted
        # transactions. We now only take the grid path if this
        # company's own taxes actually use at least one of these tags.
        tag_id_by_name = self._get_vat_grid_tags()
        if tag_id_by_name and self._company_uses_vat_grid_tags(company, tag_id_by_name):
            buckets = self._get_tax_report_buckets_by_grid(base_domain, tag_id_by_name)
        else:
            buckets = self._get_tax_report_buckets_by_name(base_domain)

        std_sales_base = buckets["std_sales"]["base"]
        std_sales_vat = buckets["std_sales"]["vat"]
        reduced_sales_base = buckets["reduced_sales"]["base"]
        reduced_sales_vat = buckets["reduced_sales"]["vat"]
        zero_sales_base = buckets["zero_sales"]["base"]
        exports_base = buckets["exports"]["base"]
        exempt_sales_base = buckets["exempt_sales"]["base"]
        std_purch_base = buckets["std_purch"]["base"]
        std_purch_vat = buckets["std_purch"]["vat"]
        import_customs_base = buckets["import_customs"]["base"]
        import_customs_vat = buckets["import_customs"]["vat"]
        import_rc_base = buckets["import_rc"]["base"]
        import_rc_vat = buckets["import_rc"]["vat"]
        zero_purch_base = buckets["zero_purch"]["base"]
        exempt_purch_base = buckets["exempt_purch"]["base"]

        total_sales_base = (
                std_sales_base + reduced_sales_base + zero_sales_base
                + exports_base + exempt_sales_base
        )
        total_sales_vat = std_sales_vat + reduced_sales_vat
        total_purch_base = (
                std_purch_base + import_customs_base + import_rc_base
                + zero_purch_base + exempt_purch_base
        )
        total_purch_vat = std_purch_vat + import_customs_vat + import_rc_vat
        total_vat_recoverable = total_purch_vat
        total_vat_due = total_sales_vat - total_vat_recoverable
        net_vat = total_vat_due

        def _line(number, name, section, line_key, base, vat,
                  style="data", show_base=True, show_vat=True, tax_ids=None):
            return {
                "number": number, "name": name, "section": section,
                "line_key": line_key,
                "base_amount": round(base, self._round_digits()),
                "vat_amount": round(vat, self._round_digits()),
                "style": style, "show_base": show_base, "show_vat": show_vat,
                "tax_ids": tax_ids or [],
            }

        all_sales_tax_ids = (
                buckets["std_sales"]["tax_ids"] + buckets["reduced_sales"]["tax_ids"]
                + buckets["zero_sales"]["tax_ids"] + buckets["exports"]["tax_ids"]
                + buckets["exempt_sales"]["tax_ids"]
        )
        all_purch_tax_ids = (
                buckets["std_purch"]["tax_ids"] + buckets["import_customs"]["tax_ids"]
                + buckets["import_rc"]["tax_ids"] + buckets["zero_purch"]["tax_ids"]
                + buckets["exempt_purch"]["tax_ids"]
        )

        lines = [
            {"section_header": True, "name": "VAT on Sales:", "section": "sales"},
            _line(1, "Standard rated sales", "sales", "std_sales",
                  std_sales_base, std_sales_vat, tax_ids=buckets["std_sales"]["tax_ids"]),
            _line(2, "Private Healthcare / Private Education / First house sales to citizens",
                  "sales", "reduced_sales", reduced_sales_base, reduced_sales_vat,
                  tax_ids=buckets["reduced_sales"]["tax_ids"]),
            _line(3, "Zero rated domestic sales", "sales", "zero_sales",
                  zero_sales_base, 0.0, show_vat=False, tax_ids=buckets["zero_sales"]["tax_ids"]),
            _line(4, "Exports", "sales", "exports",
                  exports_base, 0.0, show_vat=False, tax_ids=buckets["exports"]["tax_ids"]),
            _line(5, "Exempt sales", "sales", "exempt_sales",
                  exempt_sales_base, 0.0, show_vat=False, tax_ids=buckets["exempt_sales"]["tax_ids"]),
            _line(6, "Total Sales", "sales", "total_sales",
                  total_sales_base, total_sales_vat, style="subtotal",
                  tax_ids=all_sales_tax_ids),
            {"section_header": True, "name": "VAT on Purchases:", "section": "purchases"},
            _line(7, "Standard rated domestic purchases", "purchases", "std_purch",
                  std_purch_base, std_purch_vat, tax_ids=buckets["std_purch"]["tax_ids"]),
            _line(8, "Imports subject to VAT paid at customs", "purchases", "import_customs",
                  import_customs_base, import_customs_vat,
                  tax_ids=buckets["import_customs"]["tax_ids"]),
            _line(9, "Imports subject to VAT accounted for through reverse charge mechanism",
                  "purchases", "import_rc", import_rc_base, import_rc_vat,
                  tax_ids=buckets["import_rc"]["tax_ids"]),
            _line(10, "Zero rated purchases", "purchases", "zero_purch",
                  zero_purch_base, 0.0, show_vat=False, tax_ids=buckets["zero_purch"]["tax_ids"]),
            _line(11, "Exempt purchases", "purchases", "exempt_purch",
                  exempt_purch_base, 0.0, show_vat=False,
                  tax_ids=buckets["exempt_purch"]["tax_ids"]),
            _line(12, "Total Purchases", "purchases", "total_purch",
                  total_purch_base, total_purch_vat, style="subtotal",
                  tax_ids=all_purch_tax_ids),
            _line(13, "Total VAT due for current period", "summary", "total_vat_due",
                  0.0, total_vat_due, style="summary", show_base=False,
                  tax_ids=all_sales_tax_ids),
            _line(14, "Corrections from previous period (between +/- SAR 5000)",
                  "summary", "corrections", 0.0, 0.0, style="summary", show_base=False),
            _line(15, "VAT credit carried forward from previous period",
                  "summary", "credit_forward", 0.0, 0.0, style="summary", show_base=False),
            _line(16, "Net VAT due (or claim)", "total", "net_vat",
                  0.0, net_vat, style="total", show_base=False,
                  tax_ids=all_sales_tax_ids + all_purch_tax_ids),
        ]

        return {
            "lines": lines,
            "company_name": company.name,
            "currency_name": company.currency_id.name,
            "currency_symbol": company.currency_id.symbol,
            "currency_digits": digits,
            "date_from": date_from,
            "date_to": date_to,
        }

    # ------------------------------------------------------------------
    # Comparison helpers
    # ------------------------------------------------------------------

    def _find_line_by_id(self, lines, target_id):
        """Depth-first search for a line dict by its 'id' key anywhere in
        a hierarchical report tree."""
        for line in lines:
            if line.get("id") == target_id:
                return line
            found = self._find_line_by_id(line.get("children") or [], target_id)
            if found:
                return found
        return None

    def _add_missing_comparison_leaves(self, current_lines, comp_leaf_objects):
        """FIX (correctness bug): account lines are only built for the
        *current* period — an account whose current-period balance is
        (near) zero is dropped entirely by _account_lines(), so it never
        gets a node in ``current_lines``. If that same account had a
        real balance in a comparison period, the comparison merge below
        had nothing to attach the comparison value to and the account —
        and its comparison figure — silently vanished from the report
        instead of showing up as "0.00 / <comparison amount>".

        This inserts a zero-balance placeholder leaf for any such
        account, under the same parent section it would have belonged
        to (found via the parent_key encoded in its id, e.g.
        "bank_cash_acc_42" -> parent "bank_cash"). Because its own
        ``balance`` stays 0.0, this never changes any subtotal/total for
        the *current* period — it only makes the row (and its
        comparison column) visible.

        ``comp_leaf_objects`` is {line_id: line_dict} for every leaf
        "account" line (i.e. one that carries an ``account_id``) seen in
        any comparison period.
        """
        current_ids = set()

        def _collect(lines):
            for line in lines:
                current_ids.add(line["id"])
                if line.get("children"):
                    _collect(line["children"])

        _collect(current_lines)

        for line_id, comp_line in comp_leaf_objects.items():
            if line_id in current_ids or "_acc_" not in line_id:
                continue
            parent_key = line_id.rsplit("_acc_", 1)[0]
            parent = self._find_line_by_id(current_lines, parent_key)
            if parent is None:
                # Parent section doesn't exist in this report shape
                # (e.g. different report_type) — nothing sensible to
                # attach to, skip rather than guess.
                continue
            parent.setdefault("children", []).append({
                "id": line_id,
                "name": comp_line.get("name", ""),
                "line_type": "account",
                "style": comp_line.get("style", "account"),
                "level": comp_line.get("level", 3),
                "balance": 0.0,
                "account_id": comp_line.get("account_id"),
                "children": [],
            })
            current_ids.add(line_id)

    @api.model
    def merge_comparison_lines(self, current_lines, comparison_lines):
        """Attach comparison_balance to matching line ids recursively.

        FIX: also populate 'comparison_balances' (a single-item list) so
        PDF/screen templates can use one uniform code path whether the
        report has one comparison column or several (see
        merge_multi_comparison_lines).

        FIX (disappearing accounts): before attaching values, make sure
        every comparison-only account leaf gets a placeholder row in
        ``current_lines`` via _add_missing_comparison_leaves() — see its
        docstring for why this matters.
        """
        comp_map = {}
        comp_leaf_objects = {}

        def _flatten(lines):
            for line in lines:
                comp_map[line["id"]] = line.get("balance", 0.0)
                if line.get("account_id") is not None:
                    comp_leaf_objects[line["id"]] = line
                if line.get("children"):
                    _flatten(line["children"])

        _flatten(comparison_lines)
        self._add_missing_comparison_leaves(current_lines, comp_leaf_objects)

        def _merge(lines):
            for line in lines:
                balance = comp_map.get(line["id"], 0.0)
                line["comparison_balance"] = balance
                line["comparison_balances"] = [{"balance": balance}]
                if line.get("children"):
                    _merge(line["children"])

        _merge(current_lines)
        return current_lines

    @api.model
    def merge_multi_comparison_lines(self, current_lines, comparison_periods):
        """
        FIX: closure bug resolved — each period gets its own comp_map
        built before any nested function captures it, avoiding the
        Python late-binding closure issue.

        FIX (disappearing accounts): same placeholder-leaf insertion as
        merge_comparison_lines(), but the placeholder set is the union
        of every account seen across *all* comparison periods, so an
        account that only had a balance in, say, the 2022 comparison
        column (and not 2023, and not the current period) still shows
        up as a row with that one column populated.
        """
        period_maps = []
        all_comp_leaf_objects = {}
        for period in comparison_periods:
            # Build a fresh map for each period with no closure risk
            comp_map = {}
            period_lines = period["lines"]

            def _flatten(lines, target_map):
                for line in lines:
                    target_map[line["id"]] = line.get("balance", 0.0)
                    if (
                        line.get("account_id") is not None
                        and line["id"] not in all_comp_leaf_objects
                    ):
                        all_comp_leaf_objects[line["id"]] = line
                    if line.get("children"):
                        _flatten(line["children"], target_map)

            _flatten(period_lines, comp_map)
            period_maps.append({
                "label": period.get("label", ""),
                "date_to": period.get("date_to", ""),
                "date_from": period.get("date_from", ""),
                "balances": comp_map,
            })

        self._add_missing_comparison_leaves(current_lines, all_comp_leaf_objects)

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
                if line["comparison_balances"]:
                    line["comparison_balance"] = line["comparison_balances"][0]["balance"]
                if line.get("children"):
                    _merge(line["children"])

        _merge(current_lines)
        return current_lines

    @api.model
    def merge_tax_comparison_lines(self, current_lines, comparison_periods):
        """Attach comparison_balances list to each tax line."""
        period_maps = []
        for period in comparison_periods:
            comp_map = {}
            for line in period.get("lines", []):
                if line.get("section_header"):
                    continue
                key = line.get("line_key", "")
                comp_map[key] = {
                    "base_amount": line.get("base_amount", 0.0),
                    "vat_amount": line.get("vat_amount", 0.0),
                }
            period_maps.append({
                "label": period.get("label", ""),
                "date_to": period.get("date_to", ""),
                "date_from": period.get("date_from", ""),
                "balances": comp_map,
            })

        for line in current_lines:
            if line.get("section_header"):
                line["comparison_balances"] = []
                continue
            key = line.get("line_key", "")
            line["comparison_balances"] = [
                {
                    "label": pm["label"],
                    "date_to": pm["date_to"],
                    "date_from": pm["date_from"],
                    "base_amount": pm["balances"].get(key, {}).get("base_amount", 0.0),
                    "vat_amount": pm["balances"].get(key, {}).get("vat_amount", 0.0),
                }
                for pm in period_maps
            ]

        return current_lines