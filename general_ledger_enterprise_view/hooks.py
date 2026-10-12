# License: LGPL-3.0 or later
"""Install hooks for general_ledger_enterprise_view.

Why this exists
---------------
``account.move.line.analytic_account_ids`` is a *stored computed* Many2many.
When the module is installed on a database that already holds millions of
journal items, Odoo marks EVERY existing line for computation and runs
``_compute_analytic_account_ids`` in Python for all of them. On a large
database that means hours of install time, high memory use and a real risk of
hitting the worker time limit.

How it is avoided
-----------------
Odoo only schedules that recomputation when it has to CREATE the relation
table (``Many2many.update_db`` returns True only in that case). If the table
already exists, nothing is recomputed. So, on a FRESH install only, this
``pre_init_hook``:

  1. creates the relation table with exactly the structure Odoo would create,
  2. fills it with one set-based SQL statement per id-range (done inside
     PostgreSQL, no Python loop over records).

Odoo then finds the table, skips the recompute, and only adds the foreign keys
as usual.

Safety
------
* Runs ONLY on first install (Odoo never calls pre_init_hook on -u upgrades),
  so an already-installed database is completely unaffected.
* Everything runs inside a savepoint. If anything at all goes wrong, the
  savepoint is rolled back and Odoo falls back to its normal behaviour
  (compute in Python) - i.e. exactly what happens today.
* The relation / column names below were checked against the Odoo 19 source
  (``Many2many`` naming rule: sorted table names + ``_rel``; columns
  ``<table>_id``).
"""
import logging

from odoo.tools import SQL
from odoo.tools.sql import table_exists

_logger = logging.getLogger(__name__)

# Names Odoo 19 derives for
#   account.move.line.analytic_account_ids -> account.analytic.account
REL_TABLE = "account_analytic_account_account_move_line_rel"
COL_LINE = "account_move_line_id"
COL_ANALYTIC = "account_analytic_account_id"

_BATCH_SIZE = 200_000  # id range per INSERT ... SELECT


def _create_relation_table(cr, table=REL_TABLE, col_line=COL_LINE, col_analytic=COL_ANALYTIC):
    """Create the relation table with the same structure Odoo itself creates
    (PK on both columns + reverse index). Foreign keys are added by Odoo."""
    cr.execute(SQL(
        """
        CREATE TABLE %(rel)s (
            %(c1)s INTEGER NOT NULL,
            %(c2)s INTEGER NOT NULL,
            PRIMARY KEY (%(c1)s, %(c2)s)
        );
        COMMENT ON TABLE %(rel)s IS 'RELATION BETWEEN account_move_line AND account_analytic_account';
        CREATE INDEX ON %(rel)s (%(c2)s, %(c1)s);
        """,
        rel=SQL.identifier(table),
        c1=SQL.identifier(col_line),
        c2=SQL.identifier(col_analytic),
    ))


def _fill_relation(cr, table=REL_TABLE, col_line=COL_LINE, col_analytic=COL_ANALYTIC,
                   batch_size=_BATCH_SIZE):
    """Fill *table* from account_move_line.analytic_distribution.

    Same result as ``_compute_analytic_account_ids``: every numeric id found in
    the distribution keys (keys may be comma-separated, e.g. "12,34") that
    still exists in account_analytic_account. Returns the number of rows
    inserted. Idempotent (ON CONFLICT DO NOTHING).
    """
    cr.execute("SELECT MIN(id), MAX(id) FROM account_move_line")
    lo, hi = cr.fetchone()
    if lo is None:
        return 0

    inserted = 0
    start = lo
    while start <= hi:
        end = start + batch_size - 1
        cr.execute(SQL(
            r"""
            INSERT INTO %(rel)s (%(c1)s, %(c2)s)
            SELECT DISTINCT sub.line_id, sub.acc_id
              FROM (
                    SELECT aml.id AS line_id,
                           (regexp_matches(jsonb_object_keys(aml.analytic_distribution),
                                           '\d+', 'g'))[1]::int AS acc_id
                      FROM account_move_line aml
                     WHERE aml.id BETWEEN %(lo)s AND %(hi)s
                       AND aml.analytic_distribution IS NOT NULL
                       AND jsonb_typeof(aml.analytic_distribution) = 'object'
                   ) sub
              JOIN account_analytic_account a ON a.id = sub.acc_id
            ON CONFLICT DO NOTHING
            """,
            rel=SQL.identifier(table),
            c1=SQL.identifier(col_line),
            c2=SQL.identifier(col_analytic),
            lo=start,
            hi=end,
        ))
        inserted += cr.rowcount
        start = end + 1
    return inserted


def pre_init_hook(env):
    """Pre-build ``analytic_account_ids`` on first install (see module doc)."""
    cr = env.cr
    if table_exists(cr, REL_TABLE):
        # Already there (e.g. re-install, restored DB): let Odoo handle it.
        return
    if not table_exists(cr, "account_move_line"):
        return
    try:
        with cr.savepoint():
            _create_relation_table(cr)
            inserted = _fill_relation(cr)
        _logger.info(
            "general_ledger_enterprise_view: pre-filled %s analytic links via SQL "
            "(skips Python recompute of account.move.line.analytic_account_ids).",
            inserted,
        )
    except Exception:  # noqa: BLE001 - must never block the installation
        _logger.warning(
            "general_ledger_enterprise_view: SQL pre-fill failed; falling back to "
            "Odoo's standard computation (slower on large databases).",
            exc_info=True,
        )