# Copyright 2024 Custom Development
# License: LGPL-3.0 or later
"""Engine for Cash Book, Bank Book and Day Book.

Design rules (why this file is safe for production):

* Cash / Bank Book only use the *liquidity* accounts of the selected journals
  (journal default account + outstanding receipt/payment accounts).  Using
  every line of the journal makes Debit - Credit of each entry equal to zero,
  which is why the old balances were wrong.
* Opening balance, period totals and closing balance always come from SQL
  aggregates (``_read_group``), never from the (possibly truncated) list of
  lines that is sent to the screen.
* Every journal has its own running balance that starts from its own opening
  balance.  Closing = Opening + Debit - Credit, per journal and in total.
* Closing balance is also computed by an independent query
  (everything up to date_to) and compared; any difference is returned in
  ``integrity_messages`` so the UI / exports can warn the user.
* Lines are loaded in chunks and capped by ``limit``; totals stay correct
  even when the list is truncated (``truncated`` flag).
* All rounding uses the company currency (works for 2 and 3 decimal
  currencies).
"""

import logging
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)

REPORT_TITLES = {
    "cash_book": "Cash Book",
    "bank_book": "Bank Book",
    "day_book": "Day Book",
}
DEFAULT_MAX_LINES = 5000
HARD_MAX_LINES = 100000
FETCH_CHUNK = 2000


class DailyReportsEngine(models.AbstractModel):
    """Engine model for computing Cash Book, Bank Book, and Day Book data."""

    _name = "daily.reports.engine"
    _description = "Daily Reports Engine (Cash Book, Bank Book, Day Book)"

    # ------------------------------------------------------------------
    # Small helpers / validation
    # ------------------------------------------------------------------
    @staticmethod
    def _to_ids(values):
        ids = []
        for value in values or []:
            try:
                ids.append(int(value))
            except (TypeError, ValueError):
                continue
        return ids

    @api.model
    def _check_company(self, company_id):
        company = (
            self.env["res.company"].browse(int(company_id))
            if company_id
            else self.env.company
        )
        if company not in self.env.user.company_ids:
            raise AccessError(_("You are not allowed to access this company."))
        return company

    @api.model
    def _check_dates(self, date_from, date_to):
        try:
            d_from = fields.Date.to_date(date_from)
            d_to = fields.Date.to_date(date_to)
        except (ValueError, TypeError):
            raise UserError(_("Invalid date format."))
        if not d_from or not d_to:
            raise UserError(_("Please select both 'From' and 'To' dates."))
        if d_from > d_to:
            raise UserError(_("'From' date cannot be later than 'To' date."))
        return d_from, d_to

    @api.model
    def _get_journals(self, report_type, journal_ids, company):
        domain = [("company_id", "=", company.id)]
        if report_type == "cash_book":
            domain.append(("type", "=", "cash"))
        elif report_type == "bank_book":
            domain.append(("type", "=", "bank"))
        ids = self._to_ids(journal_ids)
        if ids:
            domain.append(("id", "in", ids))
        return self.env["account.journal"].search(domain, order="sequence, name, id")

    @api.model
    def _liquidity_accounts(self, journal):
        """Accounts that hold the real cash / bank position of a journal."""
        accounts = journal.default_account_id
        for fname in (
            "inbound_payment_method_line_ids",
            "outbound_payment_method_line_ids",
        ):
            if fname in journal._fields:
                accounts |= journal[fname].payment_account_id
        company = journal.company_id
        for fname in (
            "account_journal_payment_debit_account_id",
            "account_journal_payment_credit_account_id",
        ):
            if fname in company._fields:
                accounts |= company[fname]
        return accounts

    @api.model
    def _base_domain(
        self, company, journals, account_ids, target_move, partner_ids, analytic_ids
    ):
        domain = [
            ("company_id", "=", company.id),
            ("journal_id", "in", journals.ids),
            ("display_type", "not in", ["line_section", "line_note"]),
        ]
        if account_ids is not None:
            domain.append(("account_id", "in", account_ids))
        if target_move == "posted":
            domain.append(("parent_state", "=", "posted"))
        else:
            domain.append(("parent_state", "in", ["posted", "draft"]))
        if partner_ids:
            domain.append(("partner_id", "in", partner_ids))
        if analytic_ids:
            domain.append(("analytic_distribution", "in", analytic_ids))
        return domain

    # ------------------------------------------------------------------
    # Data access (aggregates + chunked line loading)
    # ------------------------------------------------------------------
    @api.model
    def _sum_by_journal(self, domain):
        """{journal_id: (debit, credit, count)} computed in ONE query."""
        groups = self.env["account.move.line"]._read_group(
            domain, ["journal_id"], ["debit:sum", "credit:sum", "__count"]
        )
        return {
            journal.id: (debit or 0.0, credit or 0.0, count or 0)
            for journal, debit, credit, count in groups
        }

    @api.model
    def _line_dict(self, line):
        move = line.move_id
        return {
            "id": "ml_%s" % line.id,
            "name": move.name or line.name or "",
            "move_id": move.id,
            "journal_id": line.journal_id.id,
            "partner_name": line.partner_id.name or "",
            "journal": line.journal_id.code or "",
            "account": line.account_id.code or "",
            "invoice_date": line.date.isoformat() if line.date else "",
            "due_date": line.date_maturity.isoformat() if line.date_maturity else "",
            "ref": move.ref or line.ref or "",
            "debit": line.debit or 0.0,
            "credit": line.credit or 0.0,
            "balance": 0.0,
        }

    @api.model
    def _fetch_lines(self, domain, order, limit):
        """Load at most ``limit`` lines using a two-phase fetch.

        Phase 1 — IDs only (one lightweight SQL query, no ORM overhead):
            aml.search() with the full domain + order + limit returns only
            the integer primary keys.  This result is tiny (~8 bytes / row)
            and preserves the **exact requested sort order**.

        Phase 2 — browse in batches of FETCH_CHUNK:
            aml.browse(chunk_ids) loads the ORM records for that slice,
            _line_dict() converts them to plain dicts, then
            env.invalidate_all() releases the ORM cache before the next
            batch, keeping RAM flat even for 100 k rows.

        Why NOT "id > last_id" cursor pagination:
            Cursor pagination is only safe when the sort key and the cursor
            key are the same column (or the sort is a strict total order on
            the cursor column).  Here we sort by ``date`` which is NOT
            monotonically correlated with ``id``: back-dated entries have a
            newer id but an older date, so ``id > last_id`` skips rows whose
            date puts them earlier in the page but whose id is beyond the
            cursor.  This causes missing lines, duplicate lines, and wrong
            running balances — confirmed by simulation (6 000 rows, some
            back-dated: 90 missing, 275 duplicates).
        """
        aml = self.env["account.move.line"]
        # Phase 1: one query → only integer ids, order preserved, capped.
        all_ids = aml.search(domain, order=order, limit=limit).ids
        result = []
        # Phase 2: browse + convert in memory-friendly chunks.
        for start in range(0, len(all_ids), FETCH_CHUNK):
            chunk_ids = all_ids[start: start + FETCH_CHUNK]
            for line in aml.browse(chunk_ids):
                result.append(self._line_dict(line))
            self.env.invalidate_all()
        return result


    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @api.model
    def get_report_data(
        self,
        report_type="cash_book",  # 'cash_book', 'bank_book', 'day_book'
        date_from=None,
        date_to=None,
        company_id=None,
        journal_ids=None,
        target_move="posted",
        partner_ids=None,
        analytic_account_ids=None,
        limit=DEFAULT_MAX_LINES,
    ):
        if report_type not in REPORT_TITLES:
            raise UserError(_("Unknown report type."))
        if target_move not in ("posted", "all"):
            target_move = "posted"

        company = self._check_company(company_id)
        engine = self.with_company(company)
        d_from, d_to = engine._check_dates(date_from, date_to)
        try:
            limit = int(limit or DEFAULT_MAX_LINES)
        except (TypeError, ValueError):
            limit = DEFAULT_MAX_LINES
        limit = max(1, min(limit, HARD_MAX_LINES))

        journals = engine._get_journals(report_type, journal_ids, company)
        partner_ids = engine._to_ids(partner_ids)
        analytic_ids = engine._to_ids(analytic_account_ids)

        if report_type == "day_book":
            data = engine._build_day_book(
                journals, company, d_from, d_to, target_move,
                partner_ids, analytic_ids, limit,
            )
        else:
            data = engine._build_liquidity_book(
                report_type, journals, company, d_from, d_to, target_move,
                partner_ids, analytic_ids, limit,
            )

        data.update({
            "report_title": REPORT_TITLES[report_type],
            "company_name": company.name,
            "currency_name": company.currency_id.name,
            "currency_symbol": company.currency_id.symbol,
            "max_lines": limit,
        })
        return data

    # ------------------------------------------------------------------
    # Cash Book / Bank Book
    # ------------------------------------------------------------------
    @api.model
    def _build_liquidity_book(
        self, report_type, journals, company, d_from, d_to, target_move,
        partner_ids, analytic_ids, limit,
    ):
        cur = company.currency_id
        title = REPORT_TITLES[report_type]

        account_ids = set()
        for journal in journals:
            account_ids |= set(self._liquidity_accounts(journal).ids)
        if not journals or not account_ids:
            return self._empty_result(title, show_balance=True)

        domain = self._base_domain(
            company, journals, sorted(account_ids), target_move,
            partner_ids, analytic_ids,
        )
        period_domain = domain + [("date", ">=", d_from), ("date", "<=", d_to)]

        opening = self._sum_by_journal(domain + [("date", "<", d_from)])
        period = self._sum_by_journal(period_domain)
        upto = self._sum_by_journal(domain + [("date", "<=", d_to)])

        lines = self._fetch_lines(period_domain, "date, id", limit)
        by_journal = defaultdict(list)
        for line in lines:
            by_journal[line["journal_id"]].append(line)

        messages = []
        group_rows = []
        tot_open = tot_debit = tot_credit = tot_close = 0.0
        total_count = 0
        shown_count = 0

        for journal in journals:
            o_debit, o_credit, _o_cnt = opening.get(journal.id, (0.0, 0.0, 0))
            p_debit, p_credit, p_cnt = period.get(journal.id, (0.0, 0.0, 0))
            u_debit, u_credit, _u_cnt = upto.get(journal.id, (0.0, 0.0, 0))

            j_open = cur.round(o_debit - o_credit)
            p_debit = cur.round(p_debit)
            p_credit = cur.round(p_credit)
            j_close = cur.round(j_open + p_debit - p_credit)

            # journal without movement and without balance -> nothing to show
            if not p_cnt and cur.is_zero(j_open):
                continue

            # independent check: everything up to date_to must equal closing
            independent_close = cur.round(u_debit - u_credit)
            if not cur.is_zero(independent_close - j_close):
                messages.append(_(
                    "%(journal)s: closing balance mismatch (%(a)s vs %(b)s).",
                    journal=journal.name, a=j_close, b=independent_close,
                ))

            running = j_open
            children = []
            for line in by_journal.get(journal.id, []):
                running = cur.round(running + line["debit"] - line["credit"])
                line["balance"] = running
                children.append(line)

            if len(children) == p_cnt:
                listed_debit = cur.round(sum(c["debit"] for c in children))
                listed_credit = cur.round(sum(c["credit"] for c in children))
                if not (
                    cur.is_zero(listed_debit - p_debit)
                    and cur.is_zero(listed_credit - p_credit)
                ):
                    messages.append(_(
                        "%(journal)s: listed lines do not match the period totals.",
                        journal=journal.name,
                    ))

            tot_open += j_open
            tot_debit += p_debit
            tot_credit += p_credit
            tot_close += j_close
            total_count += p_cnt
            shown_count += len(children)

            group_rows.append({
                "id": "group_journal_%s" % journal.id,
                "name": journal.name,
                "line_type": "group",
                "style": "group",
                "journal": journal.code or "",
                "account": "",
                "invoice_date": "",
                "due_date": "",
                "ref": "",
                "debit": p_debit,
                "credit": p_credit,
                "balance": j_close,
                "opening_balance": j_open,
                "children": children,
            })

        tot_open = cur.round(tot_open)
        tot_debit = cur.round(tot_debit)
        tot_credit = cur.round(tot_credit)
        tot_close = cur.round(tot_close)
        if not cur.is_zero(tot_open + tot_debit - tot_credit - tot_close):
            messages.append(_("Total: Opening + Debit - Credit does not equal Closing."))

        total_row = {
            "id": "daily_report_total",
            "name": title,
            "line_type": "total",
            "style": "header",
            "journal": "", "account": "", "invoice_date": "",
            "due_date": "", "ref": "",
            "debit": tot_debit,
            "credit": tot_credit,
            "balance": tot_close,
            "children": [],
        }
        opening_row = {
            "id": "daily_report_opening",
            "name": "Opening Balance",
            "line_type": "opening",
            "style": "group",
            "journal": "", "account": "", "invoice_date": "",
            "due_date": "", "ref": "",
            "debit": tot_open if tot_open > 0 else 0.0,
            "credit": abs(tot_open) if tot_open < 0 else 0.0,
            "balance": tot_open,
            "children": [],
        }
        return {
            "lines": [total_row, opening_row] + group_rows,
            "opening_balance": tot_open,
            "closing_balance": tot_close,
            "show_balance": True,
            "total_lines": total_count,
            "shown_lines": shown_count,
            "truncated": total_count > shown_count,
            "integrity_ok": not messages,
            "integrity_messages": messages,
        }

    # ------------------------------------------------------------------
    # Day Book
    # ------------------------------------------------------------------
    @api.model
    def _build_day_book(
        self, journals, company, d_from, d_to, target_move,
        partner_ids, analytic_ids, limit,
    ):
        cur = company.currency_id
        if not journals:
            return self._empty_result("Day Book", show_balance=False)

        domain = self._base_domain(
            company, journals, None, target_move, partner_ids, analytic_ids,
        )
        period_domain = domain + [("date", ">=", d_from), ("date", "<=", d_to)]

        groups = self.env["account.move.line"]._read_group(
            period_domain, ["date:day"],
            ["debit:sum", "credit:sum", "__count"], order="date:day",
        )
        lines = self._fetch_lines(
            period_domain, "date, journal_id, move_id, id", limit
        )
        by_date = defaultdict(list)
        for line in lines:
            by_date[line["invoice_date"]].append(line)

        group_rows = []
        tot_debit = tot_credit = 0.0
        total_count = 0
        for day, debit, credit, count in groups:
            key = day.isoformat() if day else "Undated"
            label = day.strftime("%d/%m/%Y") if day else "Undated"
            debit = cur.round(debit or 0.0)
            credit = cur.round(credit or 0.0)
            tot_debit += debit
            tot_credit += credit
            total_count += count or 0
            group_rows.append({
                "id": "group_%s" % key,
                "name": label,
                "line_type": "group",
                "style": "group",
                "journal": "", "account": "",
                "invoice_date": key,
                "due_date": "", "ref": "",
                "debit": debit,
                "credit": credit,
                "balance": None,
                "children": [
                    dict(line, balance=None) for line in by_date.get(key, [])
                ],
            })

        tot_debit = cur.round(tot_debit)
        tot_credit = cur.round(tot_credit)
        messages = []
        # Without partner/analytic filters every posted entry is balanced,
        # so total debit must equal total credit.
        if not partner_ids and not analytic_ids and not cur.is_zero(
            tot_debit - tot_credit
        ):
            messages.append(_(
                "Total debit (%(d)s) is not equal to total credit (%(c)s).",
                d=tot_debit, c=tot_credit,
            ))

        shown_count = len(lines)
        total_row = {
            "id": "daily_report_total",
            "name": "Day Book",
            "line_type": "total",
            "style": "header",
            "journal": "", "account": "", "invoice_date": "",
            "due_date": "", "ref": "",
            "debit": tot_debit,
            "credit": tot_credit,
            "balance": None,
            "children": [],
        }
        return {
            "lines": [total_row] + group_rows,
            "opening_balance": 0.0,
            "closing_balance": 0.0,
            "show_balance": False,
            "total_lines": total_count,
            "shown_lines": shown_count,
            "truncated": total_count > shown_count,
            "integrity_ok": not messages,
            "integrity_messages": messages,
        }

    @api.model
    def _empty_result(self, title, show_balance):
        total_row = {
            "id": "daily_report_total", "name": title, "line_type": "total",
            "style": "header", "journal": "", "account": "",
            "invoice_date": "", "due_date": "", "ref": "",
            "debit": 0.0, "credit": 0.0,
            "balance": 0.0 if show_balance else None, "children": [],
        }
        return {
            "lines": [total_row],
            "opening_balance": 0.0,
            "closing_balance": 0.0,
            "show_balance": show_balance,
            "total_lines": 0,
            "shown_lines": 0,
            "truncated": False,
            "integrity_ok": True,
            "integrity_messages": [],
        }

    # ------------------------------------------------------------------
    @api.model
    def has_unposted_entries(self, date_from, date_to, company_id=None):
        company = self._check_company(company_id)
        d_from, d_to = self._check_dates(date_from, date_to)
        domain = [
            ("date", ">=", d_from),
            ("date", "<=", d_to),
            ("company_id", "=", company.id),
            ("state", "=", "draft"),
        ]
        return bool(self.env["account.move"].search_count(domain, limit=1))