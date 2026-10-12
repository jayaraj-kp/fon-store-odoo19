# Copyright 2024 Custom Development
# License: LGPL-3.0 or later
"""
General Ledger & Trial Balance — Enterprise Controller
=======================================================
FIX LOG (original 11 audit issues resolved; ongoing improvements below):
  1. MOVE LINES MEMORY – compute_enterprise_gl_data now supports
     include_lines=False: period totals are computed via SQL _read_group
     (O(accounts) memory, no line loading). Line-level detail is loaded
     lazily via /gl_enterprise/get_lines (cursor-paginated, per-account).
  2. ACCESS CONTROL – _check_account_group() enforces account.group_account_user
     on every JSON route including the new /gl_enterprise/get_lines route.
  3. PDF ENGINE – replaced subprocess+wkhtmltopdf with Odoo native
     ir.qweb._render + _run_wkhtmltopdf (no shell injection, proper encoding).
  4. EXPORT STORAGE – PDF/XLSX return base64 file_content+file_name directly
     instead of permanent ir.attachment records.
  5. MOVE STATE DOMAIN – parent_state used instead of move_id.state (no join).
  6. ACCOUNT LIST BOUNDED – fallback domain now scoped to company.
  7. CURSOR PAGINATION – OFFSET replaced by id cursor iteration.
  8. GROUPED_BY – fully supports none / partners / journals with validation.
  9. DATETIME IMPORT – removed inner import datetime as dt.
  10. TESTS – see tests/ directory.
  11. MANIFEST – external_dependencies declares xlsxwriter.
Additional:
  - Analytic filtering via stored analytic_account_ids Many2many (see
    models/account_move_line.py) with proper domain builder.
  - Fiscal year start uses company.compute_fiscalyear_dates when available.
Scalability round 3:
  - TB / GL partner paging is resolved inside PostgreSQL (_sql_partner_page):
    visibility filter + name order + LIMIT/OFFSET per account; partner
    aggregates and name look-ups are limited to the requested page.
    Automatic fallback to the ORM path (and a module switch) if it fails.
  - XLSX export streams move lines page by page (_compute_streaming_xlsx_data)
    and, above _MAX_EXPORT_ROWS lines, runs as a background job
    (models/gl_export_job.py) instead of failing. PDF keeps its row cap
    (wkhtmltopdf needs the whole HTML, it cannot be streamed).
Scalability round 2:
  - Export: binary download route /gl_enterprise/export_file (no base64 in
    JSON-RPC) + xlsxwriter constant_memory. Legacy /export route kept.
  - get_lines: optional last_balance cursor -> no O(n) history aggregates.
  - Partner sub-rows: optional partner_limit/offset + /gl_enterprise/get_partners.
Documented limitations (behaviour intentionally unchanged):
  - JOURNAL GROUP RUNNING BALANCE (grouped_by="journals"): the Balance column
    of a journal sub-group counts ONLY that journal's lines (via
    /get_lines journal_id, lazy mode), starting from that journal's own
    opening balance. It is therefore NOT the account's running balance; the
    account row above it carries the real account balance. The eager
    (include_lines=True) path seeds the journal running balance with the
    account opening balance instead - the UI always uses the lazy path.
  - MULTI-CURRENCY: every debit / credit / balance / running balance in this
    report is in the COMPANY currency (account.move.line debit/credit).
    "amount_currency" and the currency code are shown per line for
    information only; there are no per-currency subtotals or revaluation and
    no foreign-currency opening balance.
Known remaining issues (see AGENTS.md):
  - /init loads all accounts/journals in one call (no server-side pagination).
  - Trial Balance Unallocated Earnings synthetic row IMPLEMENTED (FIXED).
  - Frontend lazy-loading via /get_lines is now WIRED (Issue 1 FIXED):
    toggleAccount() and togglePartner() call loadLines() on expand; template
    shows spinner + Load More button; _linesState is reactive useState.
"""

import base64
import datetime
import io
import json
import logging
import math
import urllib.parse
from collections import defaultdict

import markupsafe
from werkzeug.exceptions import InternalServerError

from odoo import _, http
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.tools import SQL

_logger = logging.getLogger(__name__)


class GlExportQueued(UserError):
    """Not a failure: the export was queued as a background job."""

_CHUNK_SIZE = 10_000
_MAX_ANALYTIC_IDS = 100
_MAX_FILTER_IDS = 10_000  # account / partner / journal filter lists
_PG_MAX_INT = 2_147_483_647  # PostgreSQL "integer" upper bound
_ALLOWED_GROUPED_BY = {"none", "partners", "journals"}
_DEFAULT_PAGE_SIZE = 80  # lines per page returned by /gl_enterprise/get_lines
_MAX_PAGE_SIZE = 500  # hard cap on page_size to prevent OOM on large requests
_ZERO_THRESHOLD = 0.005  # threshold for "effectively zero" monetary amount
_MAX_EXPORT_ROWS = 25_000  # max lines exported synchronously; bigger XLSX -> background job
_MAX_PDF_ROWS = 3_000  # PDF (wkhtmltopdf) is far heavier than XLSX -> lower cap
_MAX_SCREEN_ROWS = 20_000  # cap for the legacy include_lines=True JSON path
_DEFAULT_PARTNER_PAGE = 200  # partner sub-rows per account sent to the screen
_MAX_PARTNER_PAGE = 1000  # hard cap on a partner page
# --- Scalability round 3 -----------------------------------------------------
# (a) Partner paging is resolved inside PostgreSQL (visibility filter + name
#     order + LIMIT/OFFSET per account) instead of aggregating, loading and
#     sorting EVERY partner in Python. Safety switch: set to False to go back
#     to the previous pure-ORM behaviour. If the SQL fast path ever fails it
#     logs a warning and falls back automatically (see _sql_partner_page).
_USE_SQL_PARTNER_PAGING = True
_PARTNER_VISIBLE_EPS = 0.001  # same threshold the Python partner loop uses
# (b) XLSX export streaming. Lines are read page by page (keyset) and written
#     straight into the workbook, so memory no longer grows with the number of
#     lines. Safety switch: False -> previous eager export path.
_USE_STREAMING_XLSX = True
_EXPORT_STREAM_PAGE = 2_000  # lines read per round-trip while streaming
# Up to _MAX_EXPORT_ROWS lines are exported synchronously (as before). Bigger
# exports are queued as a background job (model gl.export.job) up to this
# hard cap. NOTE: one Excel sheet holds at most 1,048,576 rows, so the cap
# must stay safely below that (lines + account/partner header rows).
_MAX_BACKGROUND_EXPORT_ROWS = 900_000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _check_account_group():
    """Abstract access: enforce accounting group at controller layer."""
    if not request.env.user.has_group("account.group_account_user"):
        raise AccessError(_("You do not have access to General Ledger. Accounting access required."))


def _company_env(env, company):
    """Return an Environment whose context resolves company-dependent fields
    (account codes, currency, record rules) for *company*.

    NOTE: ``with_company()`` exists on RECORDSETS, not on ``Environment``;
    calling ``env.with_company(...)`` raises
    "'Environment' object has no attribute 'with_company'".
    """
    return company.with_company(company).env


def _round(currency, value):
    """Round *value* using the currency's own decimal precision."""
    if currency:
        return currency.round(value)
    return round(value, 2)


def _chunked_search_read(env, model, domain, fields, order, chunk_size=_CHUNK_SIZE):
    """Yield records using cursor-based pagination (id > last_id).

    OFFSET-based pagination does a sequential scan for large offsets in
    PostgreSQL; cursor pagination uses the indexed PK and is O(limit) per
    chunk.  Order is forced to id ASC for the cursor; callers that need a
    different logical order sort the buffered result per-account later.
    """
    last_id = 0
    Model = env[model]
    # Always append id cursor to domain
    base_domain = list(domain)
    while True:
        chunk_domain = base_domain + [("id", ">", last_id)]
        chunk = Model.search_read(
            chunk_domain,
            fields,
            order="id",
            limit=chunk_size,
        )
        if not chunk:
            break
        yield from chunk
        last_id = chunk[-1]["id"]
        if len(chunk) < chunk_size:
            break


def _get_fiscal_year_start(company, date_obj):
    """Return fiscal-year start date for *date_obj*.

    Tries company.compute_fiscalyear_dates (Odoo 19 native) first; falls
    back to fiscalyear_last_month/day legacy fields; final fallback Jan 1.
    """
    try:
        if hasattr(company, "compute_fiscalyear_dates"):
            dates = company.compute_fiscalyear_dates(date_obj)
            if dates and dates.get("date_from"):
                return dates["date_from"]
    except Exception as exc:  # noqa: BLE001 - fall back to the legacy fields
        # Not fatal (we fall back below) but never silent: a wrong fiscal-year
        # start changes every opening balance. Message at WARNING, full
        # traceback at DEBUG so a persistent failure cannot flood the log.
        _logger.warning(
            "compute_fiscalyear_dates failed for company %s (%s); "
            "falling back to the legacy fiscal-year fields.",
            getattr(company, "id", None), exc,
        )
        _logger.debug("compute_fiscalyear_dates traceback", exc_info=True)

    fy_month = getattr(company, "fiscalyear_last_month", None)
    fy_day = getattr(company, "fiscalyear_last_day", None)

    if not fy_month or not fy_day:
        return date_obj.replace(month=1, day=1)

    try:
        fy_end_this_year = datetime.date(date_obj.year, int(fy_month), int(fy_day))
        if date_obj > fy_end_this_year:
            fy_start = fy_end_this_year + datetime.timedelta(days=1)
        else:
            fy_end_prev = datetime.date(date_obj.year - 1, int(fy_month), int(fy_day))
            fy_start = fy_end_prev + datetime.timedelta(days=1)
    except ValueError as exc:
        _logger.warning(
            "Invalid legacy fiscal-year end %s/%s for company %s (%s); "
            "using January 1st as fiscal-year start.",
            fy_month, fy_day, getattr(company, "id", None), exc,
        )
        fy_start = date_obj.replace(month=1, day=1)

    return fy_start


def _sanitize_id_list(values, name):
    """Validate a list of record ids coming from the client.

    * ``None`` / empty -> ``[]`` (no filter), exactly like before.
    * Falsy entries (None, 0, "") are skipped, as the old inline code did.
      Negative ids stay valid: the UI sends ``[-1]`` to mean "match nothing".
    * Numeric strings ("12") and integral floats (12.0) are accepted.
    * Anything else (non-list, text, booleans, out-of-range numbers, absurdly
      long lists) raises UserError instead of a raw ``int()`` traceback or a
      PostgreSQL "integer out of range" error.
    Duplicates are dropped, order is kept.
    """
    if values is None or values is False or values == "":
        return []
    if not isinstance(values, (list, tuple, set, frozenset)):
        raise UserError(_("%(name)s must be a list of record ids.", name=name))
    if len(values) > _MAX_FILTER_IDS:
        raise UserError(_(
            "Too many values in %(name)s (maximum %(max)s). Please narrow the filter.",
            name=name, max=_MAX_FILTER_IDS,
        ))
    result, seen = [], set()
    for raw in values:
        if not raw:
            continue
        try:
            if isinstance(raw, bool):
                raise TypeError
            if isinstance(raw, float):
                if not raw.is_integer():
                    raise ValueError
                value = int(raw)
            elif isinstance(raw, (int, str)):
                value = int(raw)
            else:
                raise TypeError
            if abs(value) > _PG_MAX_INT:
                raise ValueError
        except (TypeError, ValueError, OverflowError) as exc:
            raise UserError(_(
                "Invalid value in %(name)s: %(value)s", name=name, value=repr(raw)[:40],
            )) from exc
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _build_analytic_domain(analytic_ids):
    """Build domain for analytic filtering using stored Many2many helper."""
    if not analytic_ids:
        return []
    try:
        ids = [int(x) for x in analytic_ids if x]
    except (TypeError, ValueError):
        return []
    if not ids:
        return []
    # Cap to avoid huge IN clause DoS
    if len(ids) > _MAX_ANALYTIC_IDS:
        _logger.warning("analytic_ids truncated from %s to %s", len(ids), _MAX_ANALYTIC_IDS)
        ids = ids[:_MAX_ANALYTIC_IDS]
    return [("analytic_account_ids", "in", ids)]


def _build_gl_base_domain(company, target_move, journal_ids=None,
                          account_ids=None, partner_ids=None, analytic_ids=None):
    """Shared domain builder for GL/TB queries.

    Used by BOTH compute_enterprise_gl_data and the get_lines route so they
    can never drift. Returns the base domain WITHOUT date bounds (those are
    added separately by each caller).
    """
    d = [
        ("company_id", "=", company.id),
        ("display_type", "not in", ["line_section", "line_note"]),
        ("parent_state", "!=", "cancel"),
    ]
    if target_move == "posted":
        d.append(("parent_state", "=", "posted"))
    elif target_move == "draft":
        d.append(("parent_state", "=", "draft"))
    # 'all' -> no additional state filter (cancel already excluded above)
    j_ids = _sanitize_id_list(journal_ids, "journal_ids")
    if j_ids:
        d.append(("journal_id", "in", j_ids))
    a_ids = _sanitize_id_list(account_ids, "account_ids")
    if a_ids:
        d.append(("account_id", "in", a_ids))
    p_ids = _sanitize_id_list(partner_ids, "partner_ids")
    if p_ids:
        d.append(("partner_id", "in", p_ids))
    d.extend(_build_analytic_domain(analytic_ids))
    return d


def _gl_account_init_balance(acc):
    """Opening balance of an account row (single source of truth for the
    screen, the PDF and the XLSX General Ledger)."""
    return float((acc.get("init_bal") or {}).get("balance") or 0.0)


def _gl_account_ending_balance(acc):
    """Closing balance of an account row = opening + period movement.

    This is the number the on-screen GL shows in its "Balance" column and in
    the grand-total row, so PDF and XLSX must use the very same value.
    Falls back to init + (debit - credit) for rows without ending_balance.
    """
    fin = acc.get("fin_bal") or {}
    ending = fin.get("ending_balance")
    if ending is not None:
        return float(ending)
    if fin.get("balance") is not None:
        return _gl_account_init_balance(acc) + float(fin["balance"])
    return _gl_account_init_balance(acc) + float(fin.get("debit") or 0.0) - float(fin.get("credit") or 0.0)


def _build_opening_balance_domains(company, date_from_obj, base_domain,
                                   has_init_bal_field=True):
    """Build the BS/PL split domains for opening balance computation.

    Returns (bs_domain, pl_domain, fallback_domain).
    - bs_domain: balance-sheet accounts (include_initial_balance=True) — ALL history before date_from
    - pl_domain: P&L accounts (include_initial_balance=False) — fiscal-year start to date_from
    - fallback_domain: used when include_initial_balance field is not available
    """
    if not has_init_bal_field:
        fy_start = _get_fiscal_year_start(company, date_from_obj)
        return [], [], base_domain + [
            ("date", ">=", fy_start),
            ("date", "<", date_from_obj),
        ]

    bs_domain = base_domain + [
        ("date", "<", date_from_obj),
        ("account_id.include_initial_balance", "=", True),
    ]
    fy_start = _get_fiscal_year_start(company, date_from_obj)
    pl_domain = base_domain + [
        ("date", ">=", fy_start),
        ("date", "<", date_from_obj),
        ("account_id.include_initial_balance", "=", False),
    ]
    return bs_domain, pl_domain, []


def _compute_opening_balance(env, account_id, date_from_obj, company,
                             partner_id=None, journal_id=None,
                             base_domain=None):
    """Compute opening balance for an account (or partner/journal group).

    Uses the same BS/PL split as compute_enterprise_gl_data:
    - Balance-sheet accounts (include_initial_balance=True): ALL history before date_from
    - P&L accounts (include_initial_balance=False): only from fiscal-year start to date_from

    Returns the opening balance as a float.
    """
    _has_init_bal_field = "include_initial_balance" in env["account.account"]._fields

    # Strip ALL date leaves from base_domain to avoid contradictions
    date_free_domain = [d for d in (base_domain or []) if d[0] != "date"]

    def _scoped(domain):
        d = list(domain)
        d.append(("account_id", "=", account_id))
        if partner_id is not None:
            d.append(("partner_id", "=", partner_id))
        if journal_id is not None:
            d.append(("journal_id", "=", journal_id))
        return d

    total = 0.0

    if _has_init_bal_field:
        # Balance-sheet: all history before date_from
        bs_domain = _scoped(date_free_domain + [
            ("date", "<", date_from_obj),
            ("account_id.include_initial_balance", "=", True),
        ])
        groups = env["account.move.line"]._read_group(
            bs_domain, groupby=[], aggregates=["debit:sum", "credit:sum"],
        )
        if groups:
            debit, credit = groups[0]
            total += (debit or 0.0) - (credit or 0.0)

        # P&L: only from fiscal-year start to date_from
        fy_start = _get_fiscal_year_start(company, date_from_obj)
        pl_domain = _scoped(date_free_domain + [
            ("date", ">=", fy_start),
            ("date", "<", date_from_obj),
            ("account_id.include_initial_balance", "=", False),
        ])
        groups = env["account.move.line"]._read_group(
            pl_domain, groupby=[], aggregates=["debit:sum", "credit:sum"],
        )
        if groups:
            debit, credit = groups[0]
            total += (debit or 0.0) - (credit or 0.0)
    else:
        # Fallback: fy_start to date_from for all accounts
        fy_start = _get_fiscal_year_start(company, date_from_obj)
        fallback_domain = _scoped(date_free_domain + [
            ("date", ">=", fy_start),
            ("date", "<", date_from_obj),
        ])
        groups = env["account.move.line"]._read_group(
            fallback_domain, groupby=[], aggregates=["debit:sum", "credit:sum"],
        )
        if groups:
            debit, credit = groups[0]
            total += (debit or 0.0) - (credit or 0.0)

    return total


def _get_move_lines_page(
        env, domain, account_id, partner_id=None, journal_id=None,
        page_size=None, last_id=0, last_date=None, currency=None, company=None,
        last_balance=None,
):
    """Fetch a page of move lines for lazy loading via /gl_enterprise/get_lines.

    Returns a dict with:
        - lines: list of move line dicts (same shape as _build_move_line_dict output)
        - balance_before: running balance before this page starts (including opening)
        - opening_balance: the account/partner/journal opening balance (before period)
        - has_more: True if there are more lines after this page
        - last_id: id of the last line in this page (for next cursor)
        - last_date: date of the last line in this page (for next cursor)

    Stable ordering: (date, id). Keyset pagination via (last_date, last_id).
    If last_date is None, starts from the beginning.

    last_balance (optional): the running balance of the last line of the
    previous page, as the client received it. When it is given together with
    last_date, balance_before is taken from it and the two whole-history
    aggregates (opening balance + balance before the cursor) are SKIPPED, so
    a deep "Load More" costs O(page_size) instead of O(lines already shown).
    opening_balance is then returned as None (only the first page needs it).
    Without last_balance the previous, fully server-side computation is used.
    """
    if page_size is None:
        page_size = _DEFAULT_PAGE_SIZE
    page_size = min(max(int(page_size), 1), _MAX_PAGE_SIZE)

    # Bug A: last_date is required when last_id > 0
    if last_id > 0 and last_date is None:
        raise ValueError("last_date is required together with last_id")

    cr = (lambda v: _round(currency, v)) if currency else (lambda v: round(v, 2))

    if last_balance is not None:
        try:
            last_balance = float(last_balance)
        except (TypeError, ValueError):
            raise ValueError("last_balance must be a number")
        if not math.isfinite(last_balance):
            raise ValueError("last_balance must be a finite number")
    use_cursor_balance = last_date is not None and last_balance is not None

    # A10: company is an explicit parameter, default to env.company
    if company is None:
        company = env.company

    # Build the scoped domain
    scoped_domain = list(domain) + [("account_id", "=", account_id)]
    if partner_id is not None:
        scoped_domain.append(("partner_id", "=", partner_id))
    if journal_id is not None:
        scoped_domain.append(("journal_id", "=", journal_id))

    # Extract date_from from domain for opening balance computation
    date_from_obj = None
    for d in domain:
        if d[0] == "date" and d[1] == ">=":
            date_from_obj = d[2]
            break

    # A11: convert date strings to date objects
    if isinstance(date_from_obj, str):
        date_from_obj = datetime.date.fromisoformat(date_from_obj)

    # Use shared helper for BS/PL split
    opening_balance = 0.0
    if date_from_obj and not use_cursor_balance:
        opening_balance = cr(_compute_opening_balance(
            env, account_id, date_from_obj, company,
            partner_id=partner_id, journal_id=journal_id,
            base_domain=domain,
        ))

    # Compute balance_before: opening + sum of debit-credit for all period lines
    # before the cursor in (date, id) order
    balance_before = opening_balance
    if use_cursor_balance:
        balance_before = cr(last_balance)
    elif last_date is not None:
        # Keyset: lines before (last_date, last_id) in (date, id) order
        before_domain = scoped_domain + [
            "|",
            ("date", "<", last_date),
            "&",
            ("date", "=", last_date),
            ("id", "<=", last_id),
        ]
        groups = env["account.move.line"]._read_group(
            before_domain,
            groupby=[],
            aggregates=["debit:sum", "credit:sum"],
        )
        if groups:
            debit, credit = groups[0]
            balance_before = cr(opening_balance + (debit or 0.0) - (credit or 0.0))

    # Fetch the page using (date, id) keyset cursor
    # Use page_size + 1 to determine has_more exactly
    fields_to_read = [
        "account_id", "date", "move_id", "journal_id", "partner_id",
        "name", "ref", "debit", "credit",
        "amount_currency", "currency_id", "matching_number",
    ]
    if last_date is not None:
        page_domain = scoped_domain + [
            "|",
            ("date", ">", last_date),
            "&",
            ("date", "=", last_date),
            ("id", ">", last_id),
        ]
    else:
        page_domain = scoped_domain
    lines_raw = env["account.move.line"].search_read(
        page_domain,
        fields_to_read,
        order="date, id",
        limit=page_size + 1,
    )
    has_more = len(lines_raw) > page_size
    lines_raw = lines_raw[:page_size]

    # Build line dicts with running balance
    cumul_balance = balance_before
    lines_out = []
    for ml in lines_raw:
        line_debit = ml.get("debit") or 0.0
        line_credit = ml.get("credit") or 0.0
        cumul_balance = cr(cumul_balance + line_debit - line_credit)

        move_id_val = ml.get("move_id")
        partner_id_val = ml.get("partner_id")
        journal_id_val = ml.get("journal_id")
        currency_id_val = ml.get("currency_id")

        if ml.get("ref") and ml.get("name"):
            ref_label = "%s - %s" % (ml["ref"], ml["name"])
        elif ml.get("ref"):
            ref_label = ml["ref"]
        elif ml.get("name"):
            ref_label = ml["name"]
        else:
            ref_label = ""

        lines_out.append({
            "id": ml["id"],
            "date": str(ml["date"]) if ml.get("date") else "",
            "move_name": move_id_val[1] if move_id_val else "",
            "move_id": move_id_val[0] if move_id_val else False,
            "journal": journal_id_val[1] if journal_id_val else "",
            "journal_id": journal_id_val[0] if journal_id_val else False,
            "partner": partner_id_val[1] if partner_id_val else "",
            "partner_id": partner_id_val[0] if partner_id_val else False,
            "ref_label": ref_label,
            "debit": line_debit,
            "credit": line_credit,
            "balance": cumul_balance,
            "amount_currency": ml.get("amount_currency") or 0.0,
            "currency": currency_id_val[1] if currency_id_val else "",
            "matching": ml.get("matching_number") or "",
        })

    new_last_id = lines_raw[-1]["id"] if lines_raw else last_id
    new_last_date = str(lines_raw[-1]["date"]) if lines_raw else (str(last_date) if last_date else None)

    return {
        "lines": lines_out,
        "balance_before": balance_before,
        "opening_balance": None if use_cursor_balance else opening_balance,
        "has_more": has_more,
        "last_id": new_last_id,
        "last_date": new_last_date,
    }



# ---------------------------------------------------------------------------
# (a) SQL partner paging
# ---------------------------------------------------------------------------

def _aml_domain_sql(env, domain):
    """Compile an account.move.line *domain* with Odoo's own domain engine
    (record rules, many2one paths, analytic helper field ...) and return the
    ``(FROM, WHERE)`` SQL fragments, so raw SQL below filters EXACTLY like the
    ORM ``_read_group`` calls it replaces."""
    query = env["account.move.line"]._search(domain)
    return query.from_clause, query.where_clause


def _sql_partner_page(env, period_domain, init_domains, scope_domain,
                      offset, limit):
    """Pick the partner sub-rows of ONE page, per account, inside PostgreSQL.

    Replicates what the Python partner loop does, for every account at once:
      * (account, partner) opening = sum of *init_domains* (balance-sheet and
        P&L split, or the legacy single domain), period = *period_domain*;
      * a partner is VISIBLE when |opening balance| > eps or period debit > eps
        or period credit > eps (the same test as the Python loop);
      * order = partner name, case-insensitive, code-point order (COLLATE "C"
        on lower(name), like Python's sorted(..., key=name.lower())); the
        "no partner" bucket (id 0) sorts as "Unknown Partner"; ties by id;
      * rows ``offset+1 .. offset+limit`` form the page, ``offset+limit+1`` is
        only a probe that tells whether another page exists.

    Returns {"order": {account_id: [partner_id, ...]},   # page, in order
             "count": {account_id: n_rows_in_page},
             "has_more": {account_id, ...},
             "domain": extra domain restricting later partner aggregates to the
                       page's partners} or None on ANY failure (the caller then
    keeps the previous behaviour, nothing else is affected).
    """
    try:
        Aml = env["account.move.line"]
        table = Aml._table

        def col(name):
            return SQL.identifier(table, name)

        parts = []
        for dom in init_domains:
            frm, whr = _aml_domain_sql(env, list(dom) + list(scope_domain))
            parts.append(SQL(
                "SELECT %(acc)s AS account_id, COALESCE(%(par)s, 0) AS pid, "
                "SUM(%(deb)s) AS i_d, SUM(%(cre)s) AS i_c, "
                "0 AS p_d, 0 AS p_c "
                "FROM %(frm)s WHERE %(whr)s "
                "GROUP BY %(acc)s, COALESCE(%(par)s, 0)",
                acc=col("account_id"), par=col("partner_id"),
                deb=col("debit"), cre=col("credit"), frm=frm, whr=whr,
            ))
        frm, whr = _aml_domain_sql(env, list(period_domain) + list(scope_domain))
        parts.append(SQL(
            "SELECT %(acc)s AS account_id, COALESCE(%(par)s, 0) AS pid, "
            "0 AS i_d, 0 AS i_c, "
            "SUM(%(deb)s) AS p_d, SUM(%(cre)s) AS p_c "
            "FROM %(frm)s WHERE %(whr)s "
            "GROUP BY %(acc)s, COALESCE(%(par)s, 0)",
            acc=col("account_id"), par=col("partner_id"),
            deb=col("debit"), cre=col("credit"), frm=frm, whr=whr,
        ))

        sql = SQL(
            """
            WITH base AS (%(union)s),
            agg AS (
                SELECT account_id, pid,
                       SUM(i_d) AS i_d, SUM(i_c) AS i_c,
                       SUM(p_d) AS p_d, SUM(p_c) AS p_c
                  FROM base
                 GROUP BY account_id, pid
            ),
            vis AS (
                SELECT * FROM agg
                 WHERE ABS(i_d - i_c) > %(eps)s
                    OR ABS(p_d) > %(eps)s
                    OR ABS(p_c) > %(eps)s
            ),
            ranked AS (
                SELECT v.account_id, v.pid,
                       ROW_NUMBER() OVER (
                           PARTITION BY v.account_id
                           ORDER BY (CASE WHEN v.pid = 0 THEN 'unknown partner'
                                          ELSE lower(COALESCE(p.name, '')) END)
                                    COLLATE "C",
                                    v.pid
                       ) AS rn
                  FROM vis v
                  LEFT JOIN res_partner p ON p.id = v.pid
            )
            SELECT account_id, pid, rn
              FROM ranked
             WHERE rn > %(off)s AND rn <= %(upper)s
             ORDER BY account_id, rn
            """,
            union=SQL(" UNION ALL ").join(parts),
            eps=_PARTNER_VISIBLE_EPS,
            off=int(offset),
            upper=int(offset) + int(limit) + 1,
        )

        env.flush_all()  # raw SQL reads the database, not the ORM cache
        with env.cr.savepoint():
            env.cr.execute(sql)
            rows = env.cr.fetchall()
    except Exception:  # noqa: BLE001 - never break the report: fall back
        _logger.warning(
            "SQL partner paging failed; falling back to the ORM path.",
            exc_info=True,
        )
        return None

    order = defaultdict(list)
    count = defaultdict(int)
    has_more = set()
    for acc_id, pid, rn in rows:
        if rn > offset + limit:
            has_more.add(acc_id)  # the probe row: one more page exists
            continue
        order[acc_id].append(pid)
        count[acc_id] += 1

    page_ids = sorted({p for pids in order.values() for p in pids if p})
    has_no_partner = any(0 in pids for pids in order.values())
    if page_ids and has_no_partner:
        domain = ["|", ("partner_id", "=", False), ("partner_id", "in", page_ids)]
    elif page_ids:
        domain = [("partner_id", "in", page_ids)]
    elif has_no_partner:
        domain = [("partner_id", "=", False)]
    else:
        domain = [("id", "in", [])]  # nothing visible: aggregate nothing
    return {"order": dict(order), "count": dict(count),
            "has_more": has_more, "domain": domain}


# ---------------------------------------------------------------------------
# (b) Streaming export helpers
# ---------------------------------------------------------------------------

class _BackgroundExportRequired(Exception):
    """The export is too big for the web request: it must run as a job."""

    def __init__(self, rows):
        super().__init__("background export required (%s rows)" % rows)
        self.rows = rows


_STREAM_LINE_FIELDS = [
    "account_id", "date", "move_id", "journal_id", "partner_id",
    "name", "ref", "debit", "credit",
    "amount_currency", "currency_id", "matching_number",
]


def _format_move_line(ml, cumul_balance, currency):
    """Same dict shape / rounding as the line dicts built by
    compute_enterprise_gl_data (single place used by the streaming export)."""
    line_debit = ml.get("debit") or 0.0
    line_credit = ml.get("credit") or 0.0
    cumul_balance = _round(currency, cumul_balance + line_debit - line_credit)

    move_id_val = ml.get("move_id")
    partner_id_val = ml.get("partner_id")
    journal_id_val = ml.get("journal_id")
    currency_id_val = ml.get("currency_id")

    if ml.get("ref") and ml.get("name"):
        ref_label = "%s - %s" % (ml["ref"], ml["name"])
    elif ml.get("ref"):
        ref_label = ml["ref"]
    elif ml.get("name"):
        ref_label = ml["name"]
    else:
        ref_label = ""

    return cumul_balance, {
        "id": ml["id"],
        "date": str(ml["date"]) if ml.get("date") else "",
        "move_name": move_id_val[1] if move_id_val else "",
        "move_id": move_id_val[0] if move_id_val else False,
        "journal": journal_id_val[1] if journal_id_val else "",
        "journal_id": journal_id_val[0] if journal_id_val else False,
        "partner": partner_id_val[1] if partner_id_val else "",
        "partner_id": partner_id_val[0] if partner_id_val else False,
        "ref_label": ref_label,
        "debit": line_debit,
        "credit": line_credit,
        "balance": cumul_balance,
        "amount_currency": ml.get("amount_currency") or 0.0,
        "currency": currency_id_val[1] if currency_id_val else "",
        "matching": ml.get("matching_number") or "",
    }


def _iter_account_lines(env, domain, account_id, partner_id=None,
                        page_size=_EXPORT_STREAM_PAGE):
    """Yield the raw lines of one account (optionally one partner; ``False``
    = lines without partner) in (date, id) order using a keyset cursor, one
    page in memory at a time. The ORM cache is dropped after every page,
    otherwise it would keep every line that was ever read."""
    Aml = env["account.move.line"]
    scoped = list(domain) + [("account_id", "=", account_id)]
    if partner_id is not None:
        scoped.append(("partner_id", "=", partner_id))
    last_date, last_id = None, 0
    while True:
        page_domain = scoped
        if last_date is not None:
            page_domain = scoped + [
                "|", ("date", ">", last_date),
                "&", ("date", "=", last_date), ("id", ">", last_id),
            ]
        rows = Aml.search_read(
            page_domain, _STREAM_LINE_FIELDS, order="date, id", limit=page_size,
        )
        if not rows:
            return
        yield from rows
        last_date, last_id = rows[-1]["date"], rows[-1]["id"]
        env.flush_all()
        env.invalidate_all()
        if len(rows) < page_size:
            return


def _stream_line_dicts(env, domain, account_id, start_balance, currency,
                       partner_id=None):
    """Generator of finished line dicts with the running balance, starting at
    *start_balance* (account or partner opening balance)."""
    cumul = float(start_balance or 0.0)
    for ml in _iter_account_lines(env, domain, account_id, partner_id):
        cumul, line = _format_move_line(ml, cumul, currency)
        yield line


def _compute_streaming_xlsx_data(env, filters, in_background=False):
    """Report data for the XLSX export with LAZY move lines.

    Totals / partner groups come from the cheap SQL-aggregated path
    (include_lines=False); every ``move_lines`` entry the XLSX writers
    iterate is a generator that reads its lines page by page. The writers
    consume each list exactly once, top to bottom, so they work unchanged.

    Raises UserError above the absolute cap and _BackgroundExportRequired
    above the synchronous cap (the caller then queues a background job).
    ``in_background=True`` (used by the job itself) skips the synchronous
    cap. Returns (report_type, data).
    """
    report_type = filters.get("report_type", "gl")
    if report_type not in ("gl", "tb"):
        report_type = "gl"
    unfold_all = bool(filters.get("unfold_all", False))
    need_lines = report_type == "gl" or unfold_all
    target_move = filters.get("target_move", "posted")
    if target_move not in ("posted", "draft", "all"):
        target_move = "posted"

    data = compute_enterprise_gl_data(
        env,
        date_from=filters.get("date_from"),
        date_to=filters.get("date_to"),
        company_id=filters.get("company_id"),
        journal_ids=filters.get("journal_ids"),
        target_move=target_move,
        hide_account_at_0=filters.get("hide_account_at_0", False),
        account_ids=filters.get("account_ids"),
        partner_ids=filters.get("partner_ids"),
        analytic_ids=filters.get("analytic_ids"),
        # The GL workbook never uses sub-groups -> do not compute them.
        grouped_by="none" if report_type == "gl" else filters.get("grouped_by", "none"),
        report_type=report_type,
        include_lines=False,
        max_lines=None,
        include_partner_groups=(report_type != "tb" or unfold_all),
    )
    if not need_lines:
        return report_type, data

    # compute_enterprise_gl_data already validated the company / dates.
    company_id = filters.get("company_id")
    company = env["res.company"].browse(int(company_id)) if company_id else env.company
    line_env = _company_env(env, company)
    currency = company.currency_id
    date_from_obj = datetime.date.fromisoformat(str(filters.get("date_from")))
    date_to_obj = datetime.date.fromisoformat(str(filters.get("date_to")))
    domain = _build_gl_base_domain(
        company, target_move,
        journal_ids=filters.get("journal_ids"),
        account_ids=filters.get("account_ids"),
        partner_ids=filters.get("partner_ids"),
        analytic_ids=filters.get("analytic_ids"),
    ) + [("date", ">=", date_from_obj), ("date", "<=", date_to_obj)]

    # Bounded count: stops at cap+1 rows, cheap on huge tables.
    rows = line_env["account.move.line"].search_count(
        domain, limit=_MAX_BACKGROUND_EXPORT_ROWS + 1)
    if rows > _MAX_BACKGROUND_EXPORT_ROWS:
        raise UserError(_(
            "This report has more than %(max)s move lines, which is too large "
            "even for a background export (an Excel sheet cannot hold more). "
            "Please narrow the date range, journals or accounts.",
            max="{:,}".format(_MAX_BACKGROUND_EXPORT_ROWS),
        ))
    if rows > _MAX_EXPORT_ROWS and not in_background:
        raise _BackgroundExportRequired(rows)

    for acc in data["accounts"]:
        if acc.get("is_unallocated_earnings"):
            continue
        acc_init = (acc.get("init_bal") or {}).get("balance", 0.0)
        if report_type == "gl":
            acc["move_lines"] = _stream_line_dicts(
                line_env, domain, acc["id"], acc_init, currency)
        elif acc.get("has_partners"):
            for pg in acc.get("partner_groups", []):
                pg["move_lines"] = _stream_line_dicts(
                    line_env, domain, acc["id"],
                    (pg.get("init_bal") or {}).get("balance", 0.0), currency,
                    partner_id=pg.get("partner_id") or False)
        else:
            acc["move_lines"] = _stream_line_dicts(
                line_env, domain, acc["id"], acc_init, currency)
    return report_type, data


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def compute_enterprise_gl_data(
        env,
        date_from,
        date_to,
        company_id=None,
        journal_ids=None,
        target_move="posted",
        hide_account_at_0=False,
        account_ids=None,
        partner_ids=None,
        analytic_ids=None,
        grouped_by="none",
        report_type="gl",
        include_lines=True,
        max_lines=None,
        partner_limit=None,
        partner_offset=0,
        include_partner_groups=True,
        **kwargs,
):
    """Compute General Ledger / Trial Balance data.

    When include_lines=True (default, backward compatible), all period move
    lines are loaded and embedded in the response (old behavior).

    When include_lines=False, period totals are computed via SQL _read_group
    aggregation (O(accounts) memory, no line loading). Move lines can be
    loaded lazily via /gl_enterprise/get_lines.

    partner_limit / partner_offset (optional, only used when include_lines is
    False): return at most partner_limit partner sub-groups per account,
    skipping the first partner_offset of them (same name order as always).
    Account totals are NOT affected. An account that has more partner groups
    than were returned carries partners_has_more=True and partner_offset_next.
    Without partner_limit every partner group is returned (previous behaviour;
    the exports rely on this).

    max_lines: when include_lines=True and max_lines is set, the number of
    period move lines is checked up-front (bounded COUNT) and a UserError is
    raised instead of loading an unbounded dataset into memory.

    Raises ValueError on bad input, AccessError on company mismatch,
    UserError when max_lines is exceeded.
    All monetary values are rounded with currency.round().
    """
    # Validate grouped_by early (kwargs silently ignored previously - issue #8)
    if grouped_by not in _ALLOWED_GROUPED_BY:
        _logger.warning("Unknown grouped_by '%s' -> fallback to 'none'", grouped_by)
        grouped_by = "none"
    # Validate target_move
    if target_move not in ("posted", "draft", "all"):
        _logger.warning("Unknown target_move '%s' -> fallback to 'posted'", target_move)
        target_move = "posted"
    # Validate report_type
    if report_type not in ("gl", "tb"):
        _logger.warning("Unknown report_type '%s' -> fallback to 'gl'", report_type)
        report_type = "gl"
    # Partner paging (optional). Invalid values are a user-facing error.
    try:
        partner_limit = int(partner_limit) if partner_limit else 0
        partner_offset = int(partner_offset) if partner_offset else 0
    except (TypeError, ValueError):
        raise UserError(_("partner_limit and partner_offset must be integers."))
    partner_limit = min(max(partner_limit, 0), _MAX_PARTNER_PAGE)
    partner_offset = max(partner_offset, 0)
    _paging = bool(partner_limit) and not include_lines
    # Also warn on unexpected kwargs instead of silently dropping
    if kwargs:
        _logger.debug("compute_enterprise_gl_data received unexpected kwargs: %s", list(kwargs.keys()))

    # --- Validate company access -------------------------------------------
    company = (
        env["res.company"].browse(int(company_id))
        if company_id
        else env.company
    )
    allowed_company_ids = env.user.company_ids.ids
    if company.id not in allowed_company_ids:
        raise AccessError(
            _("Access denied: you do not have access to company '%s'.") % company.name
        )

    # Ensure all subsequent ORM calls resolve company-dependent fields
    # (account codes, currency, etc.) using the selected company context.
    env = _company_env(env, company)
    currency = company.currency_id
    _logger.info(
        "compute_enterprise_gl_data start: company_id=%s, period=%s to %s, report_type=%s, grouped_by=%s, include_lines=%s",
        company.id, date_from, date_to, report_type, grouped_by, include_lines,
    )
    _compute_start_time = datetime.datetime.now()

    def cr(value):
        return _round(currency, value)

    def _build_move_line_dict(ml, cumul_balance):
        """Build a standardized move line dict from raw ML record.

        Returns (updated_cumul_balance, move_line_dict)
        """
        line_debit = ml.get("debit") or 0.0
        line_credit = ml.get("credit") or 0.0
        cumul_balance = cr(cumul_balance + line_debit - line_credit)

        move_id_val = ml.get("move_id")
        partner_id_val = ml.get("partner_id")
        journal_id_val = ml.get("journal_id")
        currency_id_val = ml.get("currency_id")

        if ml.get("ref") and ml.get("name"):
            ref_label = "%s - %s" % (ml["ref"], ml["name"])
        elif ml.get("ref"):
            ref_label = ml["ref"]
        elif ml.get("name"):
            ref_label = ml["name"]
        else:
            ref_label = ""

        line_dict = {
            "id": ml["id"],
            "date": str(ml["date"]) if ml.get("date") else "",
            "move_name": move_id_val[1] if move_id_val else "",
            "move_id": move_id_val[0] if move_id_val else False,
            "journal": journal_id_val[1] if journal_id_val else "",
            "journal_id": journal_id_val[0] if journal_id_val else False,
            "partner": partner_id_val[1] if partner_id_val else "",
            "partner_id": partner_id_val[0] if partner_id_val else False,
            "ref_label": ref_label,
            "debit": line_debit,
            "credit": line_credit,
            "balance": cumul_balance,
            "amount_currency": ml.get("amount_currency") or 0.0,
            "currency": currency_id_val[1] if currency_id_val else "",
            "matching": ml.get("matching_number") or "",
        }
        return cumul_balance, line_dict

    # --- Validate id filters (once; everything below receives clean lists) ---
    journal_ids = _sanitize_id_list(journal_ids, "journal_ids")
    account_ids = _sanitize_id_list(account_ids, "account_ids")
    partner_ids = _sanitize_id_list(partner_ids, "partner_ids")

    # --- Parse dates -------------------------------------------------------
    # FIX 1b: Raise on bad dates — do NOT silently fall back to "current year".
    # A silent fallback shows the wrong period without any indication to the
    # user, which is worse than an explicit error message.
    try:
        date_from_obj = datetime.date.fromisoformat(str(date_from))
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Invalid date_from value '%s'. Expected ISO format YYYY-MM-DD." % date_from
        ) from exc
    try:
        date_to_obj = datetime.date.fromisoformat(str(date_to))
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Invalid date_to value '%s'. Expected ISO format YYYY-MM-DD." % date_to
        ) from exc

    if date_from_obj > date_to_obj:
        raise ValueError(
            "date_from (%s) must not be later than date_to (%s)."
            % (date_from_obj, date_to_obj)
        )

    fy_start = _get_fiscal_year_start(company, date_from_obj)

    # --- Domain builder ----------------------------------------------------
    def _base_domain():
        d = [
            ("company_id", "=", company.id),
            ("display_type", "not in", ["line_section", "line_note"]),
            ("parent_state", "!=", "cancel"),  # Exclude cancelled moves in all modes
        ]
        # FIX #5: parent_state instead of move_id.state (no join)
        if target_move == "posted":
            d.append(("parent_state", "=", "posted"))
        elif target_move == "draft":
            d.append(("parent_state", "=", "draft"))
        # 'all' -> no additional state filter (cancel already excluded above)
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
        # FIX analytic domain via helper field + cap
        d.extend(_build_analytic_domain(analytic_ids))
        return d

    period_domain = _base_domain() + [
        ("date", ">=", date_from_obj),
        ("date", "<=", date_to_obj),
    ]

    # ROW CAP: refuse to materialise an unbounded number of move lines.
    # search_count(limit=N+1) stops counting at N+1 rows, so the check stays
    # cheap even on tables with tens of millions of rows. This runs BEFORE
    # the try/except blocks below so the UserError is not re-wrapped as a
    # generic ValueError.
    if include_lines and max_lines:
        if env["account.move.line"].search_count(period_domain, limit=max_lines + 1) > max_lines:
            raise UserError(_(
                "This report has more than %(max)s move lines, which is too large to "
                "load or export in one go. Please narrow the date range, journals or "
                "accounts. (Trial Balance without expanding rows has no limit.)",
                max="{:,}".format(max_lines),
            ))

    # FIX 1a: Split initial balance into two correct domains.
    #
    # Balance-sheet accounts (include_initial_balance=True): Bank, Receivable,
    # Payable, Capital, etc. Their balance accumulates across ALL fiscal years,
    # so opening balance must sum ALL transactions before date_from (no FY cap).
    #
    # P&L accounts (include_initial_balance=False): Revenue, Expense, etc.
    # Their balance resets at the start of each fiscal year, so opening balance
    # only includes transactions from fy_start up to date_from.
    #
    # Using a single init_domain with fy_start was wrong: balance-sheet accounts
    # in any company with >1 year of history would show the wrong opening balance
    # and Trial Balance would not tally. The test only covered single-FY scenarios.
    #
    # Odoo 19 field: account.account.include_initial_balance (Boolean).
    # If the field is absent (unexpected), we fall back to the old fy_start behaviour
    # for all accounts (safe degradation — no crash, just old inaccuracy).
    _has_init_bal_field = "include_initial_balance" in env["account.account"]._fields

    # Balance-sheet domain: ALL history before date_from
    bs_init_domain = _base_domain() + [
        ("date", "<", date_from_obj),
        ("account_id.include_initial_balance", "=", True),
    ] if _has_init_bal_field else []

    # P&L domain: only from fiscal-year start to date_from
    pl_init_domain = _base_domain() + [
        ("date", ">=", fy_start),
        ("date", "<", date_from_obj),
        ("account_id.include_initial_balance", "=", False),
    ] if _has_init_bal_field else []

    # Fallback domain (when include_initial_balance field is not available):
    # use the old single domain — fy_start to date_from, no account-type split.
    fallback_init_domain = _base_domain() + [
        ("date", ">=", fy_start),
        ("date", "<", date_from_obj),
    ] if not _has_init_bal_field else []

    # Unallocated Earnings is a company-wide figure. With any narrowing filter
    # (accounts / journals / partners / analytics) it would be a partial,
    # misleading number and the TB cannot tally anyway -> only compute and
    # show it for an unfiltered Trial Balance (also skips the extra
    # all-history aggregate for the General Ledger and filtered reports).
    def _has_ids(values):
        return any(x for x in (values or []))

    show_unallocated = (
        report_type == "tb"
        and not (
            _has_ids(journal_ids) or _has_ids(account_ids)
            or _has_ids(partner_ids) or _has_ids(analytic_ids)
        )
    )

    # --- Initial balances --------------------------------------------------
    init_by_account = {}
    try:
        def _merge_init_groups(groups):
            """Merge _read_group results into init_by_account dict."""
            for account, debit, credit in groups:
                if not account:
                    continue
                existing = init_by_account.get(account.id, {"debit": 0.0, "credit": 0.0})
                init_by_account[account.id] = {
                    "debit": cr(existing["debit"] + (debit or 0.0)),
                    "credit": cr(existing["credit"] + (credit or 0.0)),
                }

        unallocated_earnings = 0.0
        if _has_init_bal_field:
            if bs_init_domain:
                bs_groups = env["account.move.line"]._read_group(
                    bs_init_domain,
                    groupby=["account_id"],
                    aggregates=["debit:sum", "credit:sum"],
                )
                _merge_init_groups(bs_groups)
            if pl_init_domain:
                pl_groups = env["account.move.line"]._read_group(
                    pl_init_domain,
                    groupby=["account_id"],
                    aggregates=["debit:sum", "credit:sum"],
                )
                _merge_init_groups(pl_groups)
            # P&L prior earnings: all P&L transactions before fiscal-year start (date < fy_start)
            # In double-entry accounting, past P&L balances roll into Equity as Retained / Unallocated Earnings.
            if show_unallocated:
                pl_prior_domain = _base_domain() + [
                    ("date", "<", fy_start),
                    ("account_id.include_initial_balance", "=", False),
                ]
                pl_prior_groups = env["account.move.line"]._read_group(
                    pl_prior_domain,
                    groupby=[],
                    aggregates=["debit:sum", "credit:sum"],
                )
                if pl_prior_groups:
                    debit_prior, credit_prior = pl_prior_groups[0]
                    unallocated_earnings = cr((debit_prior or 0.0) - (credit_prior or 0.0))
        else:
            _logger.warning(
                "account.account.include_initial_balance field not found — "
                "falling back to fy_start-based single opening balance domain. "
                "Balance-sheet account opening balances may be incorrect for "
                "companies with multi-year data."
            )
            fallback_groups = env["account.move.line"]._read_group(
                fallback_init_domain,
                groupby=["account_id"],
                aggregates=["debit:sum", "credit:sum"],
            )
            _merge_init_groups(fallback_groups)
    except UserError:
        # Already user-facing (AccessError, ValidationError, row cap...):
        # keep its type and message instead of re-wrapping it.
        raise
    except Exception as exc:
        _logger.exception("Fatal error reading initial balances")
        raise UserError(_("Could not compute opening balances: %s", exc)) from exc

    # --- Period totals ---------------------------------------------------
    # When include_lines=True (backward compat), load all lines via chunked
    # search_read and compute totals in Python (old behavior).
    # When include_lines=False, compute totals via SQL _read_group aggregation
    # (new behavior, O(accounts) memory, no line loading).

    lines_by_account = defaultdict(list)
    all_account_ids = set(init_by_account.keys())
    # period_totals[acc_id] = {"debit": float, "credit": float}
    period_totals = {}
    # partner_period_totals[(acc_id, pid)] = {"debit": float, "credit": float}
    # Populated in include_lines=False mode when partner grouping is needed.
    partner_period_totals = {}

    # Determine grouping mode early so the include_lines=False path can reference
    # need_partner_groups when deciding whether to also compute partner period totals.
    force_partner_groups = (grouped_by == "partners")
    force_journal_groups = (grouped_by == "journals")
    need_partner_groups = include_partner_groups and (
        force_partner_groups or (report_type == "tb"))

    # PATCH (TB partner query narrowing): in the Trial Balance, partner
    # sub-rows are only ever shown for receivable / payable accounts (see
    # should_group_partners below). Restrict the (account, partner) SQL
    # aggregates to those accounts so we do not aggregate millions of lines
    # of every other account only to discard the result. When the user
    # explicitly asks for partner grouping the scope stays unrestricted, so
    # the output is identical to before in every case.
    partner_scope_domain = []
    if need_partner_groups and not force_partner_groups:
        trade_account_ids = env["account.account"].with_context(
            active_test=False
        ).search([
            ("account_type", "in", ["asset_receivable", "liability_payable"]),
        ]).ids
        partner_scope_domain = [("account_id", "in", trade_account_ids)]

    # PATCH (journal grouping in lazy mode): (account_id, journal_id) -> totals,
    # filled by SQL when include_lines=False and grouped_by == "journals".
    journal_period_totals = {}

    # (a) SQL partner paging. Only for the lazy, paged partner view (the
    # screen). Picks, per account, the partner ids of the requested page in
    # PostgreSQL; every later partner aggregate / name lookup is then limited
    # to those partners. None -> previous behaviour, unchanged.
    sql_partner_page = None
    partner_page_domain = []
    if _paging and need_partner_groups and _USE_SQL_PARTNER_PAGING:
        sql_partner_page = _sql_partner_page(
            env,
            period_domain,
            [bs_init_domain, pl_init_domain] if _has_init_bal_field
            else [fallback_init_domain],
            partner_scope_domain,
            partner_offset,
            partner_limit,
        )
        if sql_partner_page is not None:
            partner_page_domain = sql_partner_page["domain"]
    _paging_python = _paging and sql_partner_page is None

    if include_lines:
        # OLD PATH: load all lines via chunked search_read
        fields_to_read = [
            "account_id", "date", "move_id", "journal_id", "partner_id",
            "name", "ref", "debit", "credit",
            "amount_currency", "currency_id", "matching_number",
        ]
        # FIX #1 & #7: stream directly into dict, avoid holding full list in RAM
        try:
            for ml in _chunked_search_read(
                    env,
                    "account.move.line",
                    period_domain,
                    fields_to_read,
                    order="account_id, date, id",
            ):
                if ml.get("account_id"):
                    acc_id = ml["account_id"][0]
                    lines_by_account[acc_id].append(ml)
                    all_account_ids.add(acc_id)
        except UserError:
            # Already user-facing (AccessError, ValidationError, row cap...):
            # keep its type and message instead of re-wrapping it.
            raise
        except Exception as exc:
            _logger.exception("Fatal error reading period move lines")
            raise UserError(_("Could not read period move lines: %s", exc)) from exc

        # Ensure per-account lines are sorted correctly (cursor returns id order)
        for acc_lines in lines_by_account.values():
            acc_lines.sort(key=lambda x: (str(x.get("date") or ""), x["id"]))

        # Compute period totals from lines
        for acc_id, lines in lines_by_account.items():
            period_totals[acc_id] = {
                "debit": cr(sum(l.get("debit") or 0.0 for l in lines)),
                "credit": cr(sum(l.get("credit") or 0.0 for l in lines)),
            }
    else:
        # NEW PATH: SQL aggregation (no line loading)
        try:
            groups = env["account.move.line"]._read_group(
                period_domain,
                groupby=["account_id"],
                aggregates=["debit:sum", "credit:sum"],
            )
            for account, debit, credit in groups:
                if account:
                    acc_id = account.id
                    period_totals[acc_id] = {
                        "debit": cr(debit or 0.0),
                        "credit": cr(credit or 0.0),
                    }
                    all_account_ids.add(acc_id)
        except UserError:
            # Already user-facing (AccessError, ValidationError, row cap...):
            # keep its type and message instead of re-wrapping it.
            raise
        except Exception as exc:
            _logger.exception("Fatal error reading period totals")
            raise UserError(_("Could not compute period totals: %s", exc)) from exc

        # NEW PATH: also compute partner period totals via SQL when partner
        # grouping is needed, so partner figures are correct in lazy mode.
        # Without this, partner ending_balance == opening_balance because
        # period debit/credit are never accumulated.
        if need_partner_groups:
            try:
                partner_period_groups = env["account.move.line"]._read_group(
                    period_domain + partner_scope_domain + partner_page_domain,
                    groupby=["account_id", "partner_id"],
                    aggregates=["debit:sum", "credit:sum"],
                )
                for account, partner, debit, credit in partner_period_groups:
                    if not account:
                        continue
                    pid = partner.id if partner else 0
                    key = (account.id, pid)
                    existing = partner_period_totals.get(key, {"debit": 0.0, "credit": 0.0})
                    partner_period_totals[key] = {
                        "debit": cr(existing["debit"] + (debit or 0.0)),
                        "credit": cr(existing["credit"] + (credit or 0.0)),
                    }
                    all_account_ids.add(account.id)
            except UserError:
                # Already user-facing (AccessError, ValidationError, row cap...):
                # keep its type and message instead of re-wrapping it.
                raise
            except Exception as exc:
                _logger.exception("Fatal error reading partner period totals (lazy mode)")
                raise UserError(_("Could not compute partner period totals: %s", exc)) from exc

    # PATCH: lazy-mode journal sub-groups (include_lines=False). Previously the
    # journal groups were built only from loaded lines, so they were always
    # empty in lazy mode. Only runs for grouped_by == "journals" and never
    # touches the include_lines=True path.
    if force_journal_groups and not include_lines:
        try:
            for account, journal, debit, credit in env["account.move.line"]._read_group(
                    period_domain,
                    groupby=["account_id", "journal_id"],
                    aggregates=["debit:sum", "credit:sum"],
            ):
                if not account:
                    continue
                jid = journal.id if journal else 0
                journal_period_totals[(account.id, jid)] = {
                    "debit": cr(debit or 0.0),
                    "credit": cr(credit or 0.0),
                }
                all_account_ids.add(account.id)
        except UserError:
            # Already user-facing (AccessError, ValidationError, row cap...):
            # keep its type and message instead of re-wrapping it.
            raise
        except Exception as exc:
            _logger.exception("Fatal error reading journal period totals (lazy mode)")
            raise UserError(_("Could not compute journal period totals: %s", exc)) from exc

    accounts_info = {}
    if all_account_ids:
        try:
            acc_records = env["account.account"].search_read(
                [("id", "in", list(all_account_ids))],
                ["id", "code", "name", "account_type"],
            )
            for a in acc_records:
                accounts_info[a["id"]] = {
                    "code": a["code"],
                    "name": a["name"],
                    "account_type": a.get("account_type"),
                }
        except UserError:
            # Already user-facing (AccessError, ValidationError, row cap...):
            # keep its type and message instead of re-wrapping it.
            raise
        except Exception as exc:
            _logger.exception("Fatal error reading account lookup")
            raise UserError(_("Could not read chart of accounts: %s", exc)) from exc



    # FIX 2 — init_by_account_partner: conditional + correct split domains
    # Only run this expensive _read_group when partner grouping is actually needed.
    # Previously it always ran even for plain GL with grouped_by='none'.
    # Also uses the same BS/PL split as init_by_account (Fix 1a).
    init_by_account_partner = defaultdict(lambda: {"debit": 0.0, "credit": 0.0})
    if need_partner_groups:
        try:
            def _merge_partner_groups(groups):
                for account, partner, debit, credit in groups:
                    if not account:
                        continue
                    pid = partner.id if partner else 0
                    existing = init_by_account_partner.get(
                        (account.id, pid), {"debit": 0.0, "credit": 0.0}
                    )
                    init_by_account_partner[(account.id, pid)] = {
                        "debit": cr(existing["debit"] + (debit or 0.0)),
                        "credit": cr(existing["credit"] + (credit or 0.0)),
                    }

            if _has_init_bal_field:
                if bs_init_domain:
                    _merge_partner_groups(
                        env["account.move.line"]._read_group(
                            bs_init_domain + partner_scope_domain + partner_page_domain,
                            groupby=["account_id", "partner_id"],
                            aggregates=["debit:sum", "credit:sum"],
                        )
                    )
                if pl_init_domain:
                    _merge_partner_groups(
                        env["account.move.line"]._read_group(
                            pl_init_domain + partner_scope_domain + partner_page_domain,
                            groupby=["account_id", "partner_id"],
                            aggregates=["debit:sum", "credit:sum"],
                        )
                    )
            else:
                _merge_partner_groups(
                    env["account.move.line"]._read_group(
                        fallback_init_domain + partner_scope_domain + partner_page_domain,
                        groupby=["account_id", "partner_id"],
                        aggregates=["debit:sum", "credit:sum"],
                    )
                )
        except UserError:
            # Already user-facing (AccessError, ValidationError, row cap...):
            # keep its type and message instead of re-wrapping it.
            raise
        except Exception as exc:
            _logger.exception("Fatal error reading initial partner balances")
            raise UserError(_("Could not compute opening partner balances: %s", exc)) from exc

    # FIX 2 — Pre-build O(1) index: account_id → set of partner ids from init data.
    # This replaces the original quadratic scan:
    #   for (aid, pid) in init_by_account_partner.keys():
    #       if aid == acc_id:              ← scans ALL (account,partner) pairs per account
    # With 2,000 accounts × 100,000 (account,partner) pairs → 200M iterations.
    # The index is built once in O(K) where K = total distinct (account,partner) pairs.
    init_partner_ids_by_account = defaultdict(set)  # acc_id → {pid, ...}
    for (aid, pid) in init_by_account_partner.keys():
        init_partner_ids_by_account[aid].add(pid)

    # FIX 2b (Lazy mode partner-wise TB bug):
    # In lazy mode (include_lines=False), lines_by_account is empty, so partners
    # that have transactions strictly in the current period (with no opening balance)
    # were missing from partner_pids and all_partner_ids_needed.
    # Add (account, partner) keys from partner_period_totals into the index and lookup set.
    for (aid, pid) in partner_period_totals.keys():
        init_partner_ids_by_account[aid].add(pid)

    # FIX 2 — Collect ALL partner IDs and journal IDs needed across ALL accounts
    # in one pass, then fetch names in a SINGLE batch query (eliminates N+1).
    all_partner_ids_needed = set()
    all_journal_ids_needed = set()

    for acc_id, lines in lines_by_account.items():
        for ml in lines:
            if ml.get("partner_id"):
                all_partner_ids_needed.add(ml["partner_id"][0])
            if ml.get("journal_id"):
                all_journal_ids_needed.add(ml["journal_id"][0])

    # PATCH: journal ids / per-account index from SQL totals (lazy mode)
    journal_totals_by_account = defaultdict(list)
    for (aid, jid), jt in journal_period_totals.items():
        journal_totals_by_account[aid].append((jid, jt))
        if jid:
            all_journal_ids_needed.add(jid)

    # Also include partner IDs from init opening data
    for (aid, pid) in init_by_account_partner.keys():
        if pid:
            all_partner_ids_needed.add(pid)

    # Also include partner IDs from period totals (lazy mode)
    for (aid, pid) in partner_period_totals.keys():
        if pid:
            all_partner_ids_needed.add(pid)

    # Single batch fetch for ALL partner names
    global_partner_name_map = {}
    if all_partner_ids_needed:
        try:
            # active_test=False: archived partners/journals can still own entries
            p_recs = env["res.partner"].with_context(active_test=False).search_read(
                [("id", "in", list(all_partner_ids_needed))], ["id", "name"]
            )
            for pr in p_recs:
                global_partner_name_map[pr["id"]] = pr["name"] or ""
        except UserError:
            # Already user-facing (AccessError, ValidationError, row cap...):
            # keep its type and message instead of re-wrapping it.
            raise
        except Exception as exc:
            _logger.exception("Error reading partner lookup (batch)")
            raise UserError(_("Could not read partners: %s", exc)) from exc

    # Single batch fetch for ALL journal names (only when journal grouping active)
    global_journal_name_map = {}
    if force_journal_groups and all_journal_ids_needed:
        try:
            j_recs = env["account.journal"].with_context(active_test=False).search_read(
                [("id", "in", list(all_journal_ids_needed))], ["id", "name"]
            )
            for jr in j_recs:
                global_journal_name_map[jr["id"]] = jr["name"] or ""
        except Exception as exc:
            _logger.exception("Error reading journal lookup (batch)")
            # Non-fatal: names will fall back to "Unknown Journal"

    # --- Build result -------------------------------------------------------
    result = []

    for acc_id in sorted(
            all_account_ids,
            key=lambda i: accounts_info.get(i, {}).get("code", "") or "",
    ):
        if acc_id not in accounts_info:
            continue

        acc_info = accounts_info[acc_id]
        code = acc_info.get("code", "")
        name = acc_info.get("name", "")
        acc_type = acc_info.get("account_type", "")

        init = init_by_account.get(acc_id, {"debit": 0.0, "credit": 0.0})
        init_debit = init["debit"]
        init_credit = init["credit"]
        init_balance = cr(init_debit - init_credit)

        period_lines_raw = lines_by_account.get(acc_id, [])
        pt = period_totals.get(acc_id, {"debit": 0.0, "credit": 0.0})
        period_debit = pt["debit"]
        period_credit = pt["credit"]
        final_balance = cr(init_balance + period_debit - period_credit)

        cumul_balance = init_balance
        lines_out = []

        for ml in period_lines_raw:
            cumul_balance, line_dict = _build_move_line_dict(ml, cumul_balance)
            lines_out.append(line_dict)

        # --- Partner sub-groups --------------------------------------------
        is_trade_acc = acc_type in ("asset_receivable", "liability_payable")

        # FIX 2: O(1) lookup using pre-built index (was O(N) quadratic scan)
        partner_pids = set(init_partner_ids_by_account.get(acc_id, set()))
        for ml in period_lines_raw:
            pid = ml["partner_id"][0] if ml.get("partner_id") else 0
            partner_pids.add(pid)
        if sql_partner_page is not None:
            # SQL paging: only this account's page of partners is relevant.
            partner_pids = set(sql_partner_page["order"].get(acc_id, []))

        should_group_partners = need_partner_groups and bool(partner_pids) and (
                (report_type == "tb" and (is_trade_acc or force_partner_groups))
                or force_partner_groups
        )

        partner_groups = []
        partners_has_more = False
        _passed = 0
        if should_group_partners:
            lines_by_partner = defaultdict(list)
            for ml in period_lines_raw:
                pid = ml["partner_id"][0] if ml.get("partner_id") else 0
                lines_by_partner[pid].append(ml)

            # FIX 2: Use pre-fetched global map — no per-account query
            if sql_partner_page is not None:
                sorted_pids = list(sql_partner_page["order"].get(acc_id, []))
            else:
                sorted_pids = sorted(
                    list(partner_pids),
                    key=lambda p: (
                        global_partner_name_map.get(p, "Unknown Partner") if p else "Unknown Partner"
                    ).lower(),
                )

            for pid in sorted_pids:
                p_init = init_by_account_partner.get(
                    (acc_id, pid), {"debit": 0.0, "credit": 0.0}
                )
                p_init_debit = p_init["debit"]
                p_init_credit = p_init["credit"]
                p_init_balance = cr(p_init_debit - p_init_credit)

                p_lines_raw = lines_by_partner.get(pid, [])
                p_cumul_balance = p_init_balance
                p_lines_out = []

                if include_lines:
                    # Lines loaded: compute period totals from actual move lines
                    p_period_debit = 0.0
                    p_period_credit = 0.0
                    for ml in p_lines_raw:
                        line_debit = ml.get("debit") or 0.0
                        line_credit = ml.get("credit") or 0.0
                        p_period_debit = cr(p_period_debit + line_debit)
                        p_period_credit = cr(p_period_credit + line_credit)
                        p_cumul_balance, line_dict = _build_move_line_dict(ml, p_cumul_balance)
                        # Partner group uses string id for consistency with existing frontend
                        line_dict["id"] = str(line_dict["id"])
                        p_lines_out.append(line_dict)
                else:
                    # Lines NOT loaded: use SQL-aggregated partner period totals
                    # to avoid showing opening_balance == ending_balance for partners
                    _pid_key = pid if pid else 0
                    pt_p = partner_period_totals.get(
                        (acc_id, _pid_key), {"debit": 0.0, "credit": 0.0}
                    )
                    p_period_debit = pt_p["debit"]
                    p_period_credit = pt_p["credit"]
                    # Advance cumulative balance by period net movement
                    p_cumul_balance = cr(p_cumul_balance + p_period_debit - p_period_credit)

                p_name = global_partner_name_map.get(pid, "Unknown Partner") if pid else "Unknown Partner"
                p_fin_balance = p_cumul_balance
                p_period_balance = cr(p_period_debit - p_period_credit)

                if (abs(p_init_balance) > 0.001
                        or abs(p_period_debit) > 0.001
                        or abs(p_period_credit) > 0.001
                        or p_lines_out):
                    if _paging_python:
                        _passed += 1
                        if _passed <= partner_offset:
                            continue  # belongs to an earlier page
                        if len(partner_groups) >= partner_limit:
                            partners_has_more = True
                            break  # page full; one more exists
                    partner_groups.append({
                        "id": "partner_%s_%s" % (acc_id, pid),
                        "partner_id": pid,
                        "name": p_name,
                        "init_bal": {
                            "debit": cr(p_init_debit),
                            "credit": cr(p_init_credit),
                            "balance": cr(p_init_balance),
                        },
                        "fin_bal": {
                            "debit": cr(p_period_debit),
                            "credit": cr(p_period_credit),
                            "balance": p_period_balance,
                            "ending_balance": p_fin_balance,
                        },
                        "move_lines": p_lines_out,
                    })

        partner_offset_next = partner_offset + len(partner_groups)
        if sql_partner_page is not None:
            partners_has_more = acc_id in sql_partner_page["has_more"]
            partner_offset_next = partner_offset + sql_partner_page["count"].get(acc_id, 0)

        # --- Journal sub-groups --------------------------------------------
        journal_groups = []
        if force_journal_groups and period_lines_raw:
            lines_by_journal = defaultdict(list)
            for ml in period_lines_raw:
                jid = ml["journal_id"][0] if ml.get("journal_id") else 0
                lines_by_journal[jid].append(ml)

            # FIX 2: Use pre-fetched global map — no per-account query
            for jid, j_lines_raw in sorted(
                    lines_by_journal.items(),
                    key=lambda x: global_journal_name_map.get(x[0], "").lower()
            ):
                j_period_debit = cr(sum(l.get("debit") or 0.0 for l in j_lines_raw))
                j_period_credit = cr(sum(l.get("credit") or 0.0 for l in j_lines_raw))
                j_lines_out = []
                j_cumul = init_balance
                for ml in sorted(j_lines_raw, key=lambda x: (str(x.get("date") or ""), x["id"])):
                    j_cumul, line_dict = _build_move_line_dict(ml, j_cumul)
                    j_lines_out.append(line_dict)
                journal_groups.append({
                    "id": "journal_%s_%s" % (acc_id, jid),
                    "journal_id": jid,
                    "name": global_journal_name_map.get(jid, "Unknown Journal") if jid else "Unknown Journal",
                    "fin_bal": {
                        "debit": j_period_debit,
                        "credit": j_period_credit,
                        "balance": cr(j_period_debit - j_period_credit),
                    },
                    "move_lines": j_lines_out,
                })

        # PATCH: lazy mode (include_lines=False) journal sub-groups from SQL
        # totals; move lines are then loaded via /get_lines with journal_id.
        if force_journal_groups and not include_lines:
            for jid, jt in sorted(
                    journal_totals_by_account.get(acc_id, []),
                    key=lambda x: global_journal_name_map.get(x[0], "").lower(),
            ):
                if abs(jt["debit"]) < _ZERO_THRESHOLD and abs(jt["credit"]) < _ZERO_THRESHOLD:
                    continue
                journal_groups.append({
                    "id": "journal_%s_%s" % (acc_id, jid),
                    "journal_id": jid,
                    "name": global_journal_name_map.get(jid, "Unknown Journal") if jid else "Unknown Journal",
                    "fin_bal": {
                        "debit": jt["debit"],
                        "credit": jt["credit"],
                        "balance": cr(jt["debit"] - jt["credit"]),
                    },
                    "move_lines": [],
                })

        # "Hide at 0" = nothing to show: no opening balance and no period
        # movement. Must NOT depend on lines_out, which is always empty in
        # lazy mode (include_lines=False) and would wrongly hide accounts
        # whose period debit == credit.
        if (hide_account_at_0
                and abs(init_balance) < _ZERO_THRESHOLD
                and abs(period_debit) < _ZERO_THRESHOLD
                and abs(period_credit) < _ZERO_THRESHOLD):
            continue

        result.append({
            "id": acc_id,
            "code": code,
            "name": name,
            "account_type": acc_type,
            "has_partners": bool(partner_groups),
            "partner_groups": partner_groups,
            "partners_has_more": partners_has_more,
            "partner_offset_next": partner_offset_next,
            "has_journals": bool(journal_groups),
            "journal_groups": journal_groups,
            "init_bal": {
                "debit": cr(init_debit),
                "credit": cr(init_credit),
                "balance": cr(init_balance),
            },
            "fin_bal": {
                "debit": cr(period_debit),
                "credit": cr(period_credit),
                "balance": cr(period_debit - period_credit),
                "ending_balance": final_balance,
            },
            "move_lines": lines_out,
        })

    # Synthetic Unallocated Earnings row for Trial Balance:
    # In multi-year companies, P&L accounts reset at the start of each fiscal year (fy_start).
    # Without rolling the prior years' net profit/loss into Equity, the Trial Balance initial balance
    # and ending balance totals would not equal zero.
    if show_unallocated and abs(unallocated_earnings) > _ZERO_THRESHOLD:
        result.append({
            "id": "unallocated_earnings",
            "code": "",
            "name": _("Unallocated Earnings"),
            "account_type": "equity_unaffected",
            "has_partners": False,
            "partner_groups": [],
            "has_journals": False,
            "journal_groups": [],
            "init_bal": {
                "debit": cr(unallocated_earnings) if unallocated_earnings > 0 else 0.0,
                "credit": cr(-unallocated_earnings) if unallocated_earnings < 0 else 0.0,
                "balance": cr(unallocated_earnings),
            },
            "fin_bal": {
                "debit": 0.0,
                "credit": 0.0,
                "balance": 0.0,
                "ending_balance": cr(unallocated_earnings),
            },
            "move_lines": [],
            "is_unallocated_earnings": True,
        })

    _logger.info(
        "compute_enterprise_gl_data done: company_id=%s, accounts=%d, duration_ms=%s",
        company.id, len(result),
        int((datetime.datetime.now() - _compute_start_time).total_seconds() * 1000),
    )

    return {
        "accounts": result,
        "company_name": company.name,
        "currency_name": currency.name,
        "currency_symbol": currency.symbol,
        "date_from": str(date_from),

        "date_to": str(date_to),
        "fy_start": str(fy_start),
    }


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------

class GeneralLedgerEnterpriseController(http.Controller):
    """JSON HTTP controller for the Enterprise-style GL / TB OWL view."""

    # ------------------------------------------------------------------
    # /gl_enterprise/init
    # ------------------------------------------------------------------
    @http.route("/gl_enterprise/init", type="json", auth="user")
    def get_init_data(self, company_id=None):
        _check_account_group()
        env = request.env

        if company_id:
            cid = int(company_id)
            if cid not in env.user.company_ids.ids:
                raise AccessError(_("Access denied to company id %s.") % cid)
            company = env["res.company"].browse(cid)
        else:
            company = env.company

        # Resolve company-dependent fields (account codes, currency, etc.)
        # using the selected company context.
        env = _company_env(env, company)

        journals = env["account.journal"].search_read(
            [("company_id", "=", company.id)],
            ["id", "name", "code", "type"],
            order="name",
        )

        analytic_accounts = []
        try:
            analytic_accounts = env["account.analytic.account"].search_read(
                ["|", ("company_id", "=", company.id), ("company_id", "=", False)],
                ["id", "name", "code"],
                order="name",
            )
        except Exception:
            _logger.warning("Analytic accounts not available (module may not be installed).")

        companies = env["res.company"].search_read(
            [("id", "in", env.user.company_ids.ids)],
            ["id", "name"],
            order="name",
        )

        accounts = []
        try:
            # Odoo 19: account.account has NO company_id field, only the
            # many2many company_ids (required). Scoped to this company, so
            # other companies' accounts are never fetched.
            accounts = env["account.account"].search_read(
                [("company_ids", "in", [company.id])],
                ["id", "code", "name"],
                order="code",
            )
        except Exception:
            _logger.exception("Error reading accounts list")

        today_date = datetime.date.today()
        fy_start = _get_fiscal_year_start(company, today_date)
        date_from = fy_start.isoformat() if hasattr(fy_start, "isoformat") else str(fy_start)
        date_to = today_date.isoformat()
        # Company fiscal-year start (month/day) so the UI can build fiscal
        # periods for ANY year (e.g. April-March) instead of assuming Jan-Dec.
        fy_start_month = getattr(fy_start, "month", 1)
        fy_start_day = getattr(fy_start, "day", 1)

        return {
            "fiscalyear_start_month": fy_start_month,
            "fiscalyear_start_day": fy_start_day,
            "journals": journals,
            "analytic_accounts": analytic_accounts,
            "accounts": accounts,
            "companies": companies,
            "currency_name": company.currency_id.name,
            "currency_symbol": company.currency_id.symbol,
            "company_id": company.id,
            "company_name": company.name,
            "date_from": date_from,
            "date_to": date_to,
        }

    # ------------------------------------------------------------------
    # /gl_enterprise/get_data
    # ------------------------------------------------------------------
    @http.route("/gl_enterprise/get_data", type="json", auth="user")
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
            analytic_ids=None,
            grouped_by="none",
            report_type="gl",
            include_lines=True,
            partner_limit=None,
            **kwargs,
    ):
        _check_account_group()
        # Never let the client override the server-side row cap.
        kwargs.pop("max_lines", None)
        return compute_enterprise_gl_data(
            request.env,
            date_from=date_from,
            date_to=date_to,
            company_id=company_id,
            journal_ids=journal_ids,
            target_move=target_move,
            hide_account_at_0=hide_account_at_0,
            account_ids=account_ids,
            partner_ids=partner_ids,
            analytic_ids=analytic_ids,
            grouped_by=grouped_by,
            report_type=report_type,
            include_lines=include_lines,
            max_lines=_MAX_SCREEN_ROWS if include_lines else None,
            partner_limit=partner_limit,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # /gl_enterprise/get_lines  – lazy move-line loading
    # ------------------------------------------------------------------
    @http.route("/gl_enterprise/get_lines", type="json", auth="user")
    def get_lines(
            self,
            account_id,
            date_from,
            date_to,
            company_id=None,
            journal_ids=None,
            target_move="posted",
            partner_id=None,
            journal_id=None,
            page_size=None,
            last_id=0,
            last_date=None,         # BUG FIX: was missing from signature → fell into **kwargs
            account_ids=None,       # BUG FIX: filter was silently ignored
            partner_ids=None,       # BUG FIX: filter was silently ignored
            analytic_ids=None,      # BUG FIX: filter was silently ignored
            last_balance=None,      # running balance of the previous page's last line
            **kwargs,
    ):
        """Lazy-load move lines for a single account (or partner/journal group).

        Returns {lines, balance_before, opening_balance, has_more, last_id, last_date}.

        BUG FIXES applied here:
          1. last_date added to signature (was swallowed by **kwargs → page 2 always raised ValueError).
          2. account_ids / partner_ids / analytic_ids now applied to the domain so
             lazy-loaded lines match the totals shown in the header.
          3. partner_id=0 now translates to False (ORM convention for 'no partner').
          4. Uses _build_gl_base_domain (shared with compute_enterprise_gl_data) to
             eliminate the third copy of domain-building logic. The old inline copy
             had ("journal_id", "=", list) instead of "in" — a latent bug that
             _build_gl_base_domain already fixes.
        """
        _check_account_group()
        env = request.env

        # --- Validate company access -------------------------------------------
        company = (
            env["res.company"].browse(int(company_id))
            if company_id
            else env.company
        )
        if company.id not in env.user.company_ids.ids:
            raise AccessError(_("Access denied to company id %s.") % company.id)

        # Resolve company-dependent fields (account codes, currency, etc.)
        env = _company_env(env, company)

        # --- Validate account_id -----------------------------------------------
        try:
            acc_id = int(account_id)
        except (TypeError, ValueError):
            raise ValueError("Invalid account_id: %s" % account_id)
        if acc_id <= 0:
            raise ValueError("account_id must be positive")

        # --- Validate dates -----------------------------------------------------
        try:
            date_from_obj = datetime.date.fromisoformat(str(date_from))
            date_to_obj = datetime.date.fromisoformat(str(date_to))
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid date format. Expected YYYY-MM-DD.") from exc
        if date_from_obj > date_to_obj:
            raise ValueError("date_from must not be later than date_to.")

        # --- Validate page_size ---------------------------------------------------
        if page_size is not None:
            try:
                ps = int(page_size)
                if ps < 1 or ps > _MAX_PAGE_SIZE:
                    raise ValueError
            except (TypeError, ValueError):
                raise ValueError("page_size must be between 1 and %s" % _MAX_PAGE_SIZE)

        # --- Validate last_id ------------------------------------------------------
        try:
            lid = int(last_id)
            if lid < 0:
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError("last_id must be a non-negative integer")

        # Validate last_date (required when last_id > 0; checked in _get_move_lines_page too)
        if lid > 0 and last_date in (None, ""):
            raise ValueError("last_date is required when last_id > 0")
        # A malformed cursor date would otherwise reach PostgreSQL as an
        # invalid date literal. Normalise to YYYY-MM-DD (same type as before).
        if last_date in (None, ""):
            last_date = None
        else:
            try:
                last_date = datetime.date.fromisoformat(str(last_date)).isoformat()
            except (TypeError, ValueError) as exc:
                raise UserError(_(
                    "Invalid last_date '%(value)s'. Expected format YYYY-MM-DD.",
                    value=str(last_date)[:30],
                )) from exc

        # Optional cursor balance (skips the O(n) history aggregates).
        if last_balance in (None, ""):
            last_balance = None
        else:
            try:
                last_balance = float(last_balance)
            except (TypeError, ValueError) as exc:
                raise UserError(_("Invalid last_balance.")) from exc
            if not math.isfinite(last_balance):
                raise UserError(_("Invalid last_balance."))

        # --- Build base domain using shared helper --------------------------------
        # BUG FIX: replaces the third hand-rolled copy of domain logic (which had
        # journal_id "=" instead of "in") with the canonical shared builder.
        # account_ids / partner_ids / analytic_ids are now forwarded so that the
        # lines returned exactly match what compute_enterprise_gl_data counted.
        base_domain = _build_gl_base_domain(
            company,
            target_move,
            journal_ids=journal_ids,
            account_ids=account_ids,
            partner_ids=partner_ids,
            analytic_ids=analytic_ids,
        )
        domain = base_domain + [
            ("date", ">=", date_from_obj),
            ("date", "<=", date_to_obj),
        ]

        # --- Validate partner_id / journal_id ---------------------------------------
        pid = None
        if partner_id is not None:
            try:
                pid_int = int(partner_id)
                if pid_int < 0:
                    raise ValueError
                # BUG FIX: partner_id=0 means "line has no partner" → must use False,
                # not 0, otherwise ("partner_id", "=", 0) returns zero rows in PostgreSQL.
                pid = False if pid_int == 0 else pid_int
            except (TypeError, ValueError):
                raise ValueError("Invalid partner_id: %s" % partner_id)

        jid = None
        if journal_id is not None:
            try:
                jid = int(journal_id)
                if jid < 0:
                    raise ValueError
            except (TypeError, ValueError):
                raise ValueError("Invalid journal_id: %s" % journal_id)

        result = _get_move_lines_page(
            env, domain, acc_id,
            partner_id=pid, journal_id=jid,
            page_size=page_size, last_id=lid,
            last_date=last_date,
            currency=company.currency_id,
            company=company,
            last_balance=last_balance,
        )
        return result

    # ------------------------------------------------------------------
    # /gl_enterprise/get_partners  – next page of partner sub-rows
    # ------------------------------------------------------------------
    @http.route("/gl_enterprise/get_partners", type="json", auth="user")
    def get_partners(
            self,
            account_id,
            date_from,
            date_to,
            company_id=None,
            journal_ids=None,
            target_move="posted",
            partner_ids=None,
            analytic_ids=None,
            grouped_by="none",
            report_type="gl",
            offset=0,
            limit=None,
            **kwargs,
    ):
        """Return the next page of partner groups of ONE account.

        Re-uses compute_enterprise_gl_data (single source of truth for the
        numbers and the ordering) scoped to that single account, so the
        aggregates are cheap and identical to the first page's.
        Returns {partner_groups, has_more, next_offset}.
        """
        _check_account_group()
        try:
            acc_id = int(account_id)
        except (TypeError, ValueError):
            raise UserError(_("Invalid account_id."))
        if acc_id <= 0:
            raise UserError(_("Invalid account_id."))
        try:
            limit = int(limit) if limit else _DEFAULT_PARTNER_PAGE
        except (TypeError, ValueError):
            raise UserError(_("Invalid limit."))
        limit = min(max(limit, 1), _MAX_PARTNER_PAGE)
        data = compute_enterprise_gl_data(
            request.env,
            date_from=date_from,
            date_to=date_to,
            company_id=company_id,
            journal_ids=journal_ids,
            target_move=target_move,
            hide_account_at_0=False,
            account_ids=[acc_id],
            partner_ids=partner_ids,
            analytic_ids=analytic_ids,
            grouped_by=grouped_by,
            report_type=report_type,
            include_lines=False,
            partner_limit=limit,
            partner_offset=offset,
        )
        acc = next((a for a in data["accounts"] if a["id"] == acc_id), None)
        if not acc:
            return {"partner_groups": [], "has_more": False, "next_offset": 0}
        return {
            "partner_groups": acc["partner_groups"],
            "has_more": bool(acc.get("partners_has_more")),
            "next_offset": acc.get("partner_offset_next", 0),
        }

    # ------------------------------------------------------------------
    # /gl_enterprise/export  – PDF / XLSX export
    # ------------------------------------------------------------------
    @http.route("/gl_enterprise/export", type="json", auth="user")
    def export(self, export_format, filters):
        """Legacy JSON export (base64 inside the JSON-RPC answer).

        Kept unchanged for backward compatibility / fallback. The UI now uses
        /gl_enterprise/export_file (real binary download).
        """
        _check_account_group()
        env = request.env
        report_type, data = self._compute_export_data(env, export_format, filters)
        if export_format == "pdf":
            return self._export_pdf(env, report_type, data, filters)
        return self._export_xlsx(env, report_type, data, filters)

    def _compute_export_data(self, env, export_format, filters):
        """Validate the request and compute the report data (shared by the
        JSON and the binary export routes). Returns (report_type, data)."""
        if export_format not in ("pdf", "xlsx"):
            raise UserError(_("Unknown export format: %s", export_format))
        report_type = filters.get("report_type", "gl")
        unfold_all = bool(filters.get("unfold_all", False))
        max_lines = _MAX_PDF_ROWS if export_format == "pdf" else _MAX_EXPORT_ROWS

        # Determine include_lines: exports always need lines for the current
        # report type. TB without unfold_all only needs account/partner totals
        # (no move lines in the PDF/XLSX output), so we can skip line loading.
        if report_type == "tb" and not unfold_all:
            include_lines = False
        else:
            include_lines = True

        data = compute_enterprise_gl_data(
            env,
            date_from=filters.get("date_from"),
            date_to=filters.get("date_to"),
            company_id=filters.get("company_id"),
            journal_ids=filters.get("journal_ids"),
            target_move=filters.get("target_move", "posted"),
            hide_account_at_0=filters.get("hide_account_at_0", False),
            account_ids=filters.get("account_ids"),
            partner_ids=filters.get("partner_ids"),
            analytic_ids=filters.get("analytic_ids"),
            grouped_by=filters.get("grouped_by", "none"),
            report_type=report_type,
            include_lines=include_lines,
            max_lines=max_lines if include_lines else None,
            include_partner_groups=include_lines,
        )
        return report_type, data

    # ------------------------------------------------------------------
    # /gl_enterprise/export_file  – binary download (no base64, no JSON-RPC)
    # ------------------------------------------------------------------
    @staticmethod
    def _download_error_response(exc):
        """Message in the envelope the web client's download() helper shows
        (same one export_file uses for failures), returned as a normal
        response so the current transaction is committed."""
        serialize = getattr(http, "serialize_exception", None)
        if serialize:
            se = serialize(exc)
        else:
            se = {
                "name": "%s.%s" % (type(exc).__module__, type(exc).__name__),
                "message": str(exc),
                "arguments": [str(a) for a in getattr(exc, "args", ())],
                "debug": "",
            }
        error = {"code": 200, "message": "Odoo Server Error", "data": se}
        return request.make_response(str(markupsafe.escape(json.dumps(error))))

    @http.route("/gl_enterprise/export_file", type="http", auth="user",
                methods=["POST"])
    def export_file(self, export_format=None, filters=None, **kwargs):
        """Stream the PDF / XLSX as a real file response.

        The file never travels as a base64 string inside a JSON answer
        (33 % larger, held several times in browser memory). Errors are
        returned in the same envelope Odoo's own report download uses, so
        the web client's download() helper shows the real message.
        """
        try:
            _check_account_group()
            env = request.env
            try:
                filters_dict = json.loads(filters or "{}")
            except (TypeError, ValueError) as exc:
                raise UserError(_("Invalid export filters.")) from exc
            if not isinstance(filters_dict, dict):
                raise UserError(_("Invalid export filters."))
            if export_format == "xlsx" and _USE_STREAMING_XLSX:
                # Streaming: lines are read page by page while the sheet is
                # written (constant memory). Too big for a web request ->
                # queued as a background job (gl.export.job).
                try:
                    report_type, data = _compute_streaming_xlsx_data(env, filters_dict)
                except _BackgroundExportRequired as bg:
                    request.env["gl.export.job"]._queue_export(
                        filters_dict, export_format, bg.rows)
                    # RETURN (do not raise) the message: an exception would
                    # roll the transaction back and the queued job with it.
                    return self._download_error_response(GlExportQueued(_(
                        "This export has about %(rows)s lines - too large to "
                        "download directly. It is being prepared in the "
                        "background: you will get a notification when it is "
                        "ready, and you can download it from Accounting > "
                        "Reporting > Enterprise Reports > Export Files.",
                        rows="{:,}".format(bg.rows),
                    )))
            else:
                report_type, data = self._compute_export_data(
                    env, export_format, filters_dict)
            if export_format == "pdf":
                content, filename = self._build_pdf(env, report_type, data, filters_dict)
                mimetype = "application/pdf"
            else:
                content, filename = self._build_xlsx(env, report_type, data, filters_dict)
                mimetype = ("application/vnd.openxmlformats-officedocument."
                            "spreadsheetml.sheet")
        except Exception as exc:  # noqa: BLE001 - same envelope as core reports
            if not isinstance(exc, UserError):
                _logger.exception("GL export download failed")
            serialize = getattr(http, "serialize_exception", None)
            if serialize:
                se = serialize(exc)
            else:
                se = {
                    "name": "%s.%s" % (type(exc).__module__, type(exc).__name__),
                    "message": str(exc),
                    "arguments": [str(a) for a in getattr(exc, "args", ())],
                    "debug": "",
                }
            error = {"code": 200, "message": "Odoo Server Error", "data": se}
            res = request.make_response(
                str(markupsafe.escape(json.dumps(error))))
            raise InternalServerError(response=res) from exc

        quoted = urllib.parse.quote(filename)
        return request.make_response(content, headers=[
            ("Content-Type", mimetype),
            ("Content-Disposition",
             "attachment; filename=\"%s\"; filename*=UTF-8''%s" % (quoted, quoted)),
            ("Content-Length", str(len(content))),
        ])

    # ------------------------------------------------------------------
    # PDF export – Odoo native engine (no subprocess)
    # ------------------------------------------------------------------
    def _export_pdf(self, env, report_type, data, filters):
        """JSON/base64 flavour (kept for the legacy route and the tests)."""
        pdf_content, filename = self._build_pdf(env, report_type, data, filters)
        return {
            "file_content": base64.b64encode(pdf_content).decode("utf-8"),
            "file_name": filename,
        }

    def _build_pdf(self, env, report_type, data, filters):
        """Render the PDF; returns (raw bytes, filename)."""
        date_from = filters.get("date_from")
        date_to = filters.get("date_to")
        company_id = filters.get("company_id")
        company = (
            env["res.company"].browse(int(company_id)) if company_id else env.company
        )
        unfold_all = bool(filters.get("unfold_all", False))

        if report_type == "tb":
            trial_balance = []
            for acc in data.get("accounts", []):
                trial_balance.append({
                    "type": "account_type",
                    "id": acc["id"],
                    "code": acc.get("code", ""),
                    "name": acc.get("name", ""),
                    "initial_balance": acc.get("init_bal", {}).get("balance", 0.0),
                    "debit": acc.get("fin_bal", {}).get("debit", 0.0),
                    "credit": acc.get("fin_bal", {}).get("credit", 0.0),
                    "ending_balance": acc.get("fin_bal", {}).get("ending_balance", 0.0),
                    "has_partners": acc.get("has_partners", False),
                    "partner_groups": acc.get("partner_groups", []),
                    "move_lines": acc.get("move_lines", []),
                })
            report_xmlid = "general_ledger_enterprise_view.report_trial_balance_enterprise"
            pdf_data = {
                "trial_balance": trial_balance,
                "res_company": company,
                "company_currency": company.currency_id,
                "date_from": date_from,
                "date_to": date_to,
                "datetime": datetime,
                "unfold_all": unfold_all,
            }
        else:
            report_xmlid = "general_ledger_enterprise_view.report_general_ledger_enterprise"
            gl_accounts = []
            for acc in data.get("accounts", []):
                acc_copy = dict(acc)
                acc_copy["gl_init_balance"] = _gl_account_init_balance(acc)
                acc_copy["gl_ending_balance"] = _gl_account_ending_balance(acc)
                gl_accounts.append(acc_copy)
            pdf_data = {
                "accounts": gl_accounts,
                "res_company": company,
                "company_currency": company.currency_id,
                "date_from": date_from,
                "date_to": date_to,
                "datetime": datetime,
            }

        _logger.info("Generating PDF via native engine for %s", report_type)
        try:
            # FIX: DO NOT use ir.actions.report._render_qweb_pdf() /
            # _render_qweb_html() here. Confirmed by direct comparison against
            # the working Partner Ledger module: those wrapper methods run the
            # QWeb-rendered HTML through an extra lxml-based post-processing
            # step (multi-doc "article" splitting, asset link rewriting) that
            # re-serializes the document through a non-UTF-8-safe path and
            # corrupts any non-ASCII text - this is the actual cause of the
            # "Ø´Ø±ÙƒØ©" / "â€"" mojibake, not fonts and not the wkhtmltopdf
            # binary. Partner Ledger avoids this entirely by never calling
            # _render_qweb_pdf/_render_qweb_html; it renders HTML itself and
            # calls _run_wkhtmltopdf() directly. We do the same here, but
            # still render through our existing QWeb template (no template
            # rewrite needed) via the low-level ir.qweb renderer.
            html = env["ir.qweb"]._render(report_xmlid, pdf_data)

            report_obj = env["ir.actions.report"]
            paperformat = env.ref(
                "general_ledger_enterprise_view.paperformat_enterprise_gl",
                raise_if_not_found=False,
            )
            if paperformat:
                report_obj = report_obj.new({"paperformat_id": paperformat.id})

            pdf_content = report_obj._run_wkhtmltopdf(
                [html],
                landscape=False,
                specific_paperformat_args={
                    "data-report-margin-top": 12,
                    "data-report-margin-bottom": 8,
                    "data-report-margin-left": 5,
                    "data-report-margin-right": 5,
                },
            )
        except UserError:
            # Already user-facing (AccessError, ValidationError, row cap...):
            # keep its type and message instead of re-wrapping it.
            raise
        except Exception as exc:
            _logger.exception("PDF rendering failed")
            raise UserError(_("PDF generation failed: %s", exc)) from exc

        filename = (
            "general_ledger_%s_%s.pdf" % (date_from, date_to)
            if report_type == "gl"
            else "trial_balance_%s_%s.pdf" % (date_from, date_to)
        )
        return pdf_content, filename

    # ------------------------------------------------------------------
    # XLSX export
    # ------------------------------------------------------------------
    def _export_xlsx(self, env, report_type, data, filters):
        """JSON/base64 flavour (kept for the legacy route and the tests)."""
        content, filename = self._build_xlsx(env, report_type, data, filters)
        return {
            "file_content": base64.b64encode(content).decode("utf-8"),
            "file_name": filename,
        }

    def _build_xlsx(self, env, report_type, data, filters, path=None):
        """Generate the XLSX with xlsxwriter.

        Returns (raw bytes, filename). When ``path`` is given the workbook is
        written to that file on disk and ``None`` is returned instead of the
        bytes (used by the background export job).
        """
        try:
            import xlsxwriter
        except ImportError as exc:
            raise UserError(_(
                "XLSX export requires the 'xlsxwriter' Python package. "
                "Install it with: pip install xlsxwriter"
            )) from exc

        date_from = filters.get("date_from")
        date_to = filters.get("date_to")
        company_id = filters.get("company_id")
        company = (
            env["res.company"].browse(int(company_id)) if company_id else env.company
        )
        currency = company.currency_id
        num_fmt = "#,##0." + "0" * currency.decimal_places
        # FIX: honor the "unfold all" filter in the XLSX export the same way
        # the PDF export already does, so an unfolded export contains the
        # partner-group / move-line breakdown instead of just account totals.
        unfold_all = bool(filters.get("unfold_all", False))

        output = None if path else io.BytesIO()
        # constant_memory: rows are flushed to a temp file as they are written
        # instead of the whole sheet living in RAM. Safe here because every
        # writer below emits rows strictly top-to-bottom.
        workbook = xlsxwriter.Workbook(path or output, {"constant_memory": True})

        fmt_title = workbook.add_format({"bold": True, "font_size": 14, "bottom": 1})
        fmt_header = workbook.add_format({
            "bold": True, "font_size": 11, "bg_color": "#F0F0F0",
            "bottom": 1, "align": "center",
        })
        fmt_bold = workbook.add_format({"bold": True, "font_size": 11, "bottom": 1, "top": 1})
        fmt_bold.set_num_format(num_fmt)
        fmt_amount = workbook.add_format({"font_size": 11})
        fmt_amount.set_num_format(num_fmt)
        fmt_date = workbook.add_format({"align": "center", "font_size": 11})
        fmt_text = workbook.add_format({"font_size": 11})
        fmt_indent = workbook.add_format({"font_size": 11, "indent": 1})
        # Detail-row formats for the "unfold all" breakdown (partner groups /
        # move lines) inside the Trial Balance export - mirrors the PDF's
        # indentation levels (partner row = level 1, move line = level 2).
        fmt_partner_text = workbook.add_format({
            "font_size": 10, "italic": True, "bold": True, "indent": 2,
        })
        fmt_partner_amount = workbook.add_format({
            "font_size": 10, "italic": True, "bold": True,
        })
        fmt_partner_amount.set_num_format(num_fmt)
        fmt_detail_text = workbook.add_format({"font_size": 9, "indent": 3})
        fmt_detail_amount = workbook.add_format({"font_size": 9})
        fmt_detail_amount.set_num_format(num_fmt)

        accounts = data.get("accounts", [])
        sheet = workbook.add_worksheet("Report")

        if report_type == "tb":
            self._write_tb_xlsx(
                sheet, workbook, accounts, currency, data,
                fmt_title, fmt_header, fmt_bold, fmt_amount, fmt_text, fmt_indent,
                fmt_partner_text, fmt_partner_amount, fmt_detail_text, fmt_detail_amount,
                unfold_all,
            )
        else:
            self._write_gl_xlsx(
                sheet, workbook, accounts, currency, data,
                fmt_title, fmt_header, fmt_bold, fmt_amount, fmt_text, fmt_date, fmt_indent,
            )

        workbook.close()

        filename = (
            "general_ledger_%s_%s.xlsx" % (date_from, date_to)
            if report_type == "gl"
            else "trial_balance_%s_%s.xlsx" % (date_from, date_to)
        )
        return (None if path else output.getvalue()), filename

    def _write_gl_xlsx(
            self, sheet, workbook, accounts, currency, data,
            fmt_title, fmt_header, fmt_bold, fmt_amount, fmt_text, fmt_date, fmt_indent,
    ):

        sheet.merge_range(0, 0, 0, 5, "General Ledger", fmt_title)
        sheet.write(1, 0, "Period: %s to %s" % (data.get("date_from", ""), data.get("date_to", "")), fmt_text)
        sheet.write(2, 0, "Company: %s" % data.get("company_name", ""), fmt_text)
        row = 4

        for col, h in enumerate(["Date", "Entry", "Partner", "Debit", "Credit", "Balance"]):
            sheet.write(row, col, h, fmt_header)
        row += 1

        sheet.set_column(0, 0, 12)
        sheet.set_column(1, 1, 18)
        sheet.set_column(2, 2, 30)
        sheet.set_column(3, 3, 16)
        sheet.set_column(4, 4, 16)
        sheet.set_column(5, 5, 16)

        grand_debit = 0.0
        grand_credit = 0.0

        for acc in accounts:
            sheet.write(row, 0, "%s %s" % (acc.get("code", ""), acc.get("name", "")), fmt_bold)
            sheet.write(row, 1, "", fmt_bold)
            sheet.write(row, 2, "", fmt_bold)
            fin = acc.get("fin_bal", {})
            acc_init = _gl_account_init_balance(acc)
            acc_ending = _gl_account_ending_balance(acc)
            sheet.write_number(row, 3, float(fin.get("debit", 0.0)), fmt_bold)
            sheet.write_number(row, 4, float(fin.get("credit", 0.0)), fmt_bold)
            sheet.write_number(row, 5, float(acc_ending), fmt_bold)
            grand_debit = currency.round(grand_debit + fin.get("debit", 0.0))
            grand_credit = currency.round(grand_credit + fin.get("credit", 0.0))
            row += 1

            # Opening row (same as PDF): lines below start from this balance.
            if abs(acc_init) >= 0.005:
                sheet.write_string(row, 0, "", fmt_indent)
                sheet.write_string(row, 1, "Initial Balance", fmt_text)
                sheet.write_string(row, 2, "", fmt_text)
                sheet.write_blank(row, 3, None, fmt_amount)
                sheet.write_blank(row, 4, None, fmt_amount)
                sheet.write_number(row, 5, float(acc_init), fmt_amount)
                row += 1

            running = acc_init
            for ml in acc.get("move_lines", []):
                running = currency.round(running + ml.get("debit", 0.0) - ml.get("credit", 0.0))
                date_val = ml.get("date", "")
                if hasattr(date_val, "strftime"):
                    date_str = date_val.strftime("%d/%m/%Y")
                else:
                    date_str = str(date_val) if date_val else ""

                sheet.write_string(row, 0, date_str, fmt_indent)
                sheet.write_string(row, 1, ml.get("move_name", ""), fmt_text)
                sheet.write_string(row, 2, ml.get("partner", ""), fmt_text)
                sheet.write_number(row, 3, float(ml.get("debit", 0.0)), fmt_amount)
                sheet.write_number(row, 4, float(ml.get("credit", 0.0)), fmt_amount)
                sheet.write_number(row, 5, float(running), fmt_amount)
                row += 1

            row += 1

        row += 1
        sheet.write(row, 0, "Total", fmt_bold)
        sheet.write(row, 1, "", fmt_bold)
        sheet.write(row, 2, "", fmt_bold)
        sheet.write_number(row, 3, grand_debit, fmt_bold)
        sheet.write_number(row, 4, grand_credit, fmt_bold)
        # No Balance in the grand total: GL has no Unallocated Earnings row,
        # so opening/ending would not net to zero (same as the screen & PDF).
        sheet.write_blank(row, 5, None, fmt_bold)

    def _write_tb_xlsx(
            self, sheet, workbook, accounts, currency, data,
            fmt_title, fmt_header, fmt_bold, fmt_amount, fmt_text, fmt_indent,
            fmt_partner_text, fmt_partner_amount, fmt_detail_text, fmt_detail_amount,
            unfold_all=False,
    ):

        sheet.merge_range(0, 0, 0, 5, "Trial Balance", fmt_title)
        sheet.write(1, 0, "Period: %s to %s" % (data.get("date_from", ""), data.get("date_to", "")), fmt_text)
        sheet.write(2, 0, "Company: %s" % data.get("company_name", ""), fmt_text)
        row = 4

        for col, h in enumerate(["Code", "Account Name", "Opening Balance", "Debit", "Credit", "Closing Balance"]):
            sheet.write(row, col, h, fmt_header)
        row += 1

        sheet.set_column(0, 0, 12)
        sheet.set_column(1, 1, 60)
        sheet.set_column(2, 2, 18)
        sheet.set_column(3, 3, 16)
        sheet.set_column(4, 4, 16)
        sheet.set_column(5, 5, 18)

        decimals = currency.decimal_places

        def _line_label(ml, show_partner):
            """Mirror the PDF's move-line label: entry (· partner) - no date,
            no ref_label (tax name / product name) per user request."""
            label = ml.get("move_name", "") or ""
            if show_partner and ml.get("partner"):
                label = "%s · %s" % (label, ml.get("partner", "")) if label else ml.get("partner", "")
            return label

        totals = {"initial": 0.0, "debit": 0.0, "credit": 0.0, "ending": 0.0}

        for acc in accounts:
            init_bal = acc.get("init_bal", {}).get("balance", 0.0)
            fin = acc.get("fin_bal", {})
            fin_debit = fin.get("debit", 0.0)
            fin_credit = fin.get("credit", 0.0)
            fin_ending = fin.get("ending_balance", fin.get("balance", 0.0))

            if (abs(init_bal) < 0.005 and abs(fin_debit) < 0.005
                    and abs(fin_credit) < 0.005 and abs(fin_ending) < 0.005):
                continue

            sheet.write_string(row, 0, acc.get("code", ""), fmt_indent)
            sheet.write_string(row, 1, acc.get("name", ""), fmt_text)
            sheet.write_number(row, 2, float(init_bal), fmt_amount)
            sheet.write_number(row, 3, float(fin_debit), fmt_amount)
            sheet.write_number(row, 4, float(fin_credit), fmt_amount)
            sheet.write_number(row, 5, float(fin_ending), fmt_amount)
            row += 1

            totals["initial"] = currency.round(totals["initial"] + init_bal)
            totals["debit"] = currency.round(totals["debit"] + fin_debit)
            totals["credit"] = currency.round(totals["credit"] + fin_credit)
            totals["ending"] = currency.round(totals["ending"] + fin_ending)

            # FIX: when "unfold all" is active, add the same breakdown the
            # PDF export shows - partner sub-groups (for receivable/payable
            # style accounts) with their move lines, or the plain move lines
            # for accounts with no partner grouping.
            if not unfold_all:
                continue

            if acc.get("has_partners"):
                for pg in acc.get("partner_groups", []):
                    pg_init = pg.get("init_bal", {}).get("balance", 0.0)
                    pg_fin = pg.get("fin_bal", {})
                    pg_debit = pg_fin.get("debit", 0.0)
                    pg_credit = pg_fin.get("credit", 0.0)
                    pg_ending = pg_fin.get("ending_balance", pg_fin.get("balance", 0.0))

                    sheet.write_string(row, 0, "", fmt_partner_text)
                    sheet.write_string(row, 1, pg.get("name", ""), fmt_partner_text)
                    sheet.write_number(row, 2, float(pg_init), fmt_partner_amount)
                    sheet.write_number(row, 3, float(pg_debit), fmt_partner_amount)
                    sheet.write_number(row, 4, float(pg_credit), fmt_partner_amount)
                    sheet.write_number(row, 5, float(pg_ending), fmt_partner_amount)
                    row += 1

                    for ml in pg.get("move_lines", []):
                        sheet.write_string(row, 0, "", fmt_detail_text)
                        sheet.write_string(row, 1, _line_label(ml, show_partner=False), fmt_detail_text)
                        sheet.write_blank(row, 2, None, fmt_detail_amount)
                        sheet.write_number(row, 3, float(ml.get("debit", 0.0)), fmt_detail_amount)
                        sheet.write_number(row, 4, float(ml.get("credit", 0.0)), fmt_detail_amount)
                        sheet.write_number(row, 5, float(ml.get("balance", 0.0)), fmt_detail_amount)
                        row += 1
            else:
                for ml in acc.get("move_lines", []):
                    sheet.write_string(row, 0, "", fmt_detail_text)
                    sheet.write_string(row, 1, _line_label(ml, show_partner=True), fmt_detail_text)
                    sheet.write_blank(row, 2, None, fmt_detail_amount)
                    sheet.write_number(row, 3, float(ml.get("debit", 0.0)), fmt_detail_amount)
                    sheet.write_number(row, 4, float(ml.get("credit", 0.0)), fmt_detail_amount)
                    sheet.write_number(row, 5, float(ml.get("balance", 0.0)), fmt_detail_amount)
                    row += 1

        row += 1
        sheet.write(row, 0, "", fmt_bold)
        sheet.write(row, 1, "Total", fmt_bold)
        sheet.write_number(row, 2, totals["initial"], fmt_bold)
        sheet.write_number(row, 3, totals["debit"], fmt_bold)
        sheet.write_number(row, 4, totals["credit"], fmt_bold)
        sheet.write_number(row, 5, totals["ending"], fmt_bold)

    # ------------------------------------------------------------------
    # Inline CSS for PDF (no external assets)
    # ------------------------------------------------------------------
    @staticmethod
    def _get_report_css():
        return """
* { box-sizing: border-box; }
body {
    /* FIX: Arabic-capable fonts must come BEFORE DejaVu Sans. DejaVu Sans has no
       Arabic contextual shaping (joined letterforms) and wkhtmltopdf's WebKit font
       matcher will grab it first in the old order, producing garbled/mis-mapped
       glyphs for Arabic text. Noto fonts must also be installed as OS fonts on the
       server running wkhtmltopdf - see install command below. */
    font-family: 'Noto Naskh Arabic','Noto Sans Arabic','DejaVu Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 "Helvetica Neue", Arial, sans-serif;
    font-size: 14px; color: #212529; margin: 0; padding: 0;
    unicode-bidi: plaintext; /* let each text node auto-detect its own direction */
}
.amount { font-family: 'DejaVu Sans', monospace !important; unicode-bidi: isolate; }
/* Cells that can contain mixed "English / Arabic" partner/account names */
.act_as_cell, td, th { unicode-bidi: plaintext; }
.page { padding: 0; }
table { width: 100% !important; border-collapse: collapse !important; }
th, td { word-wrap: break-word !important; }
.act_as_table {
    display: table !important; width: 100% !important;
    table-layout: fixed !important; border-collapse: collapse !important;
    border: none; background: transparent;
}
.act_as_thead { display: table-header-group !important; }
.act_as_row   { display: table-row   !important; border: none; background: transparent; }
.act_as_cell  { display: table-cell  !important; border: none; background: transparent; }
.act_as_row.labels { border-bottom: 2px solid #495057; font-weight: bold; margin-bottom: 4px; }
.act_as_row.labels .act_as_cell { font-weight: bold; padding: 5px 6px; font-size: 13px; }
.act_as_row:not(.labels) .act_as_cell {
    padding: 5px 6px; vertical-align: middle; font-size: 14px;
    border-bottom: 1px solid #e3e3e3;
}
.oca-gl-pdf-accrow { margin-top: 10px; }
.oca-gl-pdf-accrow .act_as_cell { font-weight: bold; padding-top: 7px; padding-bottom: 7px; }
.oca-gl-pdf-moveline .act_as_cell { color: #212529; vertical-align: top; }
.act_as_cell.amount, .act_as_cell.right {
    text-align: right; font-variant-numeric: tabular-nums;
}
.act_as_cell.left { text-align: left; }
.oca-gl-pdf-companyheader { display: table; width: 100%; margin-bottom: 4px; }
.oca-gl-pdf-companyleft   { display: table-cell; width: 65%; vertical-align: top; text-align: left; }
.oca-gl-pdf-companyright  { display: table-cell; width: 35%; vertical-align: top; text-align: right; }
.oca-gl-pdf-logo          { max-height: 55px; max-width: 180px; display: block; margin-bottom: 4px; }
.oca-gl-pdf-companyname   { font-weight: 700; font-size: 14px; }
.oca-gl-pdf-companycountry, .oca-gl-pdf-companyvat { font-size: 12px; color: #6c757d; }
.oca-gl-pdf-title         { font-size: 18px; font-weight: 700; margin: 0; }
.oca-gl-pdf-period {
    display: block; width: 100%; text-align: center;
    background-color: #f0f0f0; color: #343a40; font-weight: 600;
    font-size: 13px; padding: 8px 0; margin: 12px 0 6px 0; border-radius: 3px;
}
.oca_gl_pdf_entry, .oca_gl_pdf_truncate {
    white-space: normal; overflow: visible; max-width: 100%;
    display: block; line-height: 1.35; word-break: break-word;
}
.oca-gl-pdf-zero   { color: #adb5bd; }
.oca-gl-pdf-header .act_as_cell    { font-weight: bold; }
.oca-gl-pdf-grandtotal .act_as_cell { font-weight: bold; font-size: 14px; }
.oca-tb-pdf-header-block            { width: 100%; margin-bottom: 4px; }
.oca-tb-pdf-companycenter           { text-align: center; }
.oca-tb-pdf-title-center            { text-align: center; margin-top: 6px; }
.oca-tb-pdf-period-left             { text-align: left; font-size: 13px; font-weight: 600; margin-top: 8px; }
.oca-tb-pdf-header-table            { border-collapse: collapse; width: 100%; margin-top: 4px; }
.oca-tb-pdf-header-table th         { font-size: 14px; font-weight: bold; padding: 6px; border-bottom: 2px solid #495057; }
div.oca-tb-pdf-lines div.act_as_row div.act_as_cell          { font-size: 16px; padding: 6px; }
div.oca-tb-pdf-lines div.oca-gl-pdf-accrow div.act_as_cell   { font-size: 16px; font-weight: bold; }
div.oca-tb-pdf-lines div.oca-gl-pdf-partner-row div.act_as_cell { font-size: 14px; font-style: italic; font-weight: 600; }
div.oca-tb-pdf-grandtotal div.act_as_cell { font-size: 16px; font-weight: bold; }
"""