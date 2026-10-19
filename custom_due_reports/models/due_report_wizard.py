# -*- coding: utf-8 -*-
from datetime import date
import re
import json
import logging
from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError
from odoo.tools import SQL

_logger = logging.getLogger(__name__)


class DueReportWizard(models.TransientModel):
    _name = 'due.report.wizard'
    _description = 'Customer / Vendor Due Report Wizard'

    move_type = fields.Selection(
        [('out_invoice', 'Customer Due Report'),
         ('in_invoice', 'Vendor Due Report')],
        string='Report Type', required=True, default='out_invoice',
    )
    date_from = fields.Date(
        string='From Date', required=False, default=False,
    )
    date_to = fields.Date(
        string='To Date', required=True,
        default=lambda self: fields.Date.context_today(self),
    )
    partner_ids = fields.Many2many(
        'res.partner', string='Customers / Vendors',
        help='Leave empty to include all partners.',
    )
    analytic_account_ids = fields.Many2many(
        'account.analytic.account', string='Analytic Accounts',
        help='Leave empty to include all analytic accounts.',
    )
    only_due = fields.Boolean(
        string='Only Outstanding (Balance > 0)', default=True,
        help='Show only invoices/bills that still have an outstanding balance.',
    )
    due_filter = fields.Selection(
        [('all', 'All Outstanding'),
         ('upcoming', 'Upcoming Due'),
         ('overdue', 'Overdue')],
        string='Due Status Filter', default='all',
    )
    search_query = fields.Char(
        string='Search',
        help='Same text as the on-screen search box: only the partners / documents '
             'matching it are printed and exported.',
    )
    show_grand_total = fields.Boolean(
        string='Show Grand Total in PDF', default=True,
        help='If enabled, prints the Grand Total Summary at the end of the PDF report.',
    )
    show_address = fields.Boolean(
        string='Show Address in PDF', default=False,
        help='If enabled, prints each partner\'s email, phone and address under their name.',
    )
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, required=True,
    )

    # ------------------------------------------------------------------
    # Domain / data helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _get_move_types(move_type):
        if move_type in ('out_invoice', 'out_refund'):
            return ('out_invoice', 'out_refund')
        if move_type in ('in_invoice', 'in_refund'):
            return ('in_invoice', 'in_refund')
        return (move_type,)

    def _get_domain(self):
        """Returns the base search domain for candidate moves (without large ID filters)."""
        self.ensure_one()
        move_types = self._get_move_types(self.move_type)
        domain = [
            ('move_type', 'in', move_types),
            ('state', '=', 'posted'),
            ('company_id', '=', self.company_id.id),
        ]
        if self.date_from:
            domain.append(('invoice_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('invoice_date', '<=', self.date_to))
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))
        return domain

    def _fetch_report_moves(self, company, move_types, date_from=None, date_to=None,
                            partner_ids=None, only_due=True, as_of_date=None,
                            analytic_account_ids=None):
        """Fetch moves for the due report directly from PostgreSQL.

        Avoids loading all historical candidate moves into Python memory.
        Uses Move.search for open moves and Move._search().subselect() with
        SQL UNION ALL for moves reconciled after as_of_date.
        Returns account.move recordset.
        """
        Move = self.env['account.move']
        domain = [
            ('move_type', 'in', move_types),
            ('state', '=', 'posted'),
            ('company_id', '=', company.id),
        ]
        if date_from and str(date_from).strip() not in ('false', 'null', 'undefined', ''):
            domain.append(('invoice_date', '>=', str(date_from).strip()))
        if date_to and str(date_to).strip() not in ('false', 'null', 'undefined', ''):
            domain.append(('invoice_date', '<=', str(date_to).strip()))
        if partner_ids:
            domain.append(('partner_id', 'in', list(partner_ids)))

        if not only_due:
            moves = Move.search(domain, order='invoice_date asc, id asc')
            if analytic_account_ids:
                moves = self._filter_moves_by_analytic(moves, analytic_account_ids)
            return moves

        # ------------------------------------------------------------------
        # only_due = True:
        # ------------------------------------------------------------------
        if as_of_date is None:
            as_of_date = date_to or fields.Date.context_today(self)
        as_of_str = fields.Date.to_string(as_of_date) if hasattr(as_of_date, 'strftime') else str(as_of_date)

        # 1. Invoices currently open: filtered by DB directly!
        # Fully settled, historic invoices never enter Python memory.
        open_ids = set(Move.search(domain + [('amount_residual', '!=', 0.0)], order='id').ids)

        # 2. Invoices matching domain that were paid, but reconciled AFTER as_of_date.
        # Uses Move._search(domain).subselect() so candidate moves are NOT fetched into RAM.
        query = Move._search(domain)
        reconciled_after_ids = set()
        try:
            reconcile_sql = SQL(
                """
                SELECT DISTINCT sub.move_id
                  FROM (
                    SELECT aml.move_id
                      FROM account_partial_reconcile apr
                      JOIN account_move_line aml ON aml.id = apr.debit_move_id
                     WHERE aml.move_id IN %s
                       AND apr.max_date > %s
                    UNION ALL
                    SELECT aml.move_id
                      FROM account_partial_reconcile apr
                      JOIN account_move_line aml ON aml.id = apr.credit_move_id
                     WHERE aml.move_id IN %s
                       AND apr.max_date > %s
                  ) sub
                """,
                query.subselect(),
                as_of_str,
                query.subselect(),
                as_of_str,
            )
            # Savepoint: a failing query must not abort the whole transaction.
            with self.env.cr.savepoint():
                self.env.cr.execute(reconcile_sql)
                reconciled_after_ids = {r[0] for r in self.env.cr.fetchall()}
        except Exception as exc:
            # Never continue silently: without this list, invoices that were
            # paid AFTER the report date would be dropped and balances understated.
            _logger.exception("Due report: error querying future reconciliations via subselect.")
            raise UserError(
                "The due report could not be computed (reconciliation lookup failed). "
                "Please contact your administrator. Details: %s" % exc
            )

        due_ids = open_ids | reconciled_after_ids
        if not due_ids:
            return Move.browse()

        # 3. Analytic filter on the matching due_ids if specified
        if analytic_account_ids:
            analytic_matching_ids = self._get_analytic_move_ids_sql(due_ids, analytic_account_ids)
            if analytic_matching_ids is not None:
                due_ids = due_ids & analytic_matching_ids
                if not due_ids:
                    return Move.browse()
            else:
                moves = Move.browse(list(due_ids))
                return self._filter_moves_by_analytic(moves, analytic_account_ids)

        return Move.browse(list(due_ids))

    def _get_moves(self, as_of_date=None):
        """Returns the filtered account.move recordset for this wizard instance."""
        self.ensure_one()
        move_types = self._get_move_types(self.move_type)
        as_of = as_of_date or self.date_to or fields.Date.context_today(self)
        return self._fetch_report_moves(
            company=self.company_id,
            move_types=move_types,
            date_from=self.date_from,
            date_to=self.date_to,
            partner_ids=self.partner_ids.ids if self.partner_ids else None,
            only_due=self.only_due,
            as_of_date=as_of,
            analytic_account_ids=self.analytic_account_ids.ids if self.analytic_account_ids else None,
        )

    def _get_future_reconciled_amounts(self, moves, as_of_date):
        """Calculates partial reconciliations dated AFTER as_of_date for the given moves.
        Returns: {move_id: {'amount_currency': float, 'amount_company': float}}

        Uses UNION ALL so each of the two FK indexes (debit_move_id, credit_move_id)
        is used independently — no sequential scan from an OR predicate.
        """
        if not moves or not as_of_date:
            return {}
        as_of_str = fields.Date.to_string(as_of_date) if hasattr(as_of_date, 'strftime') else str(as_of_date)
        move_ids = list(moves.ids)
        if not move_ids:
            return {}

        query = """
            SELECT move_id,
                   SUM(future_doc) AS future_doc,
                   SUM(future_co)  AS future_co
              FROM (
                -- Debit side: the move's line is the debit leg
                SELECT aml.move_id,
                       COALESCE(NULLIF(apr.debit_amount_currency, 0.0), apr.amount)  AS future_doc,
                       apr.amount                                                     AS future_co
                  FROM account_partial_reconcile apr
                  JOIN account_move_line aml ON aml.id = apr.debit_move_id
                 WHERE aml.move_id = ANY(%s)
                   AND apr.max_date > %s
                UNION ALL
                -- Credit side: the move's line is the credit leg
                SELECT aml.move_id,
                       COALESCE(NULLIF(apr.credit_amount_currency, 0.0), apr.amount) AS future_doc,
                       apr.amount                                                     AS future_co
                  FROM account_partial_reconcile apr
                  JOIN account_move_line aml ON aml.id = apr.credit_move_id
                 WHERE aml.move_id = ANY(%s)
                   AND apr.max_date > %s
              ) sub
             GROUP BY move_id
        """
        self.env.cr.execute(query, (move_ids, as_of_str, move_ids, as_of_str))
        res = {}
        for row in self.env.cr.fetchall():
            res[row[0]] = {
                'amount_currency': float(row[1] or 0.0),
                'amount_company': float(row[2] or 0.0),
            }
        return res

    def _get_analytic_move_ids_sql(self, move_ids, analytic_ids):
        """Return a set of move_ids (subset of *move_ids*) that have at least
        one journal-entry line touching any of *analytic_ids*.

        Strategy (fastest first):
          1. Use the stored Many2many relation table
             ``account_move_line_account_analytic_account_rel`` that
             ``general_ledger_enterprise_view`` creates on
             ``account.move.line.analytic_account_ids``.  This is a pure
             JOIN — no Python iteration and no JSON parsing.
          2. Fall back to an ORM domain on ``analytic_distribution`` (the
             field's own search implementation handles the JSON column).
          3. If even that fails, return None so the caller can use the old
             Python loop as a last resort.
        """
        if not move_ids or not analytic_ids:
            return set()

        analytic_ids_list = list(analytic_ids)
        cr = self.env.cr

        # --- Strategy 1: stored M2M relation table (O(log n) index JOIN) ---
        AML = self.env['account.move.line']
        field = AML._fields.get('analytic_account_ids')
        rel_tables = []
        if (field and field.type == 'many2many' and field.store
                and getattr(field, 'relation', None)):
            rel_tables.append((field.relation, field.column1, field.column2))
        rel_tables.extend([
            ('account_analytic_account_account_move_line_rel', 'account_move_line_id', 'account_analytic_account_id'),
            ('account_move_line_account_analytic_account_rel', 'account_move_line_id', 'account_analytic_account_id'),
        ])

        seen_tables = set()
        for rel_table, col_line, col_analytic in rel_tables:
            if rel_table in seen_tables:
                continue
            seen_tables.add(rel_table)
            try:
                # Savepoint instead of cr.rollback(): a missing table must only
                # undo this lookup, never the whole transaction (which would
                # also delete the wizard record created just before printing).
                with cr.savepoint():
                    cr.execute(SQL(
                        """
                        SELECT DISTINCT aml.move_id
                          FROM account_move_line aml
                          JOIN %(rel)s rel ON rel.%(col_line)s = aml.id
                         WHERE aml.move_id = ANY(%(move_ids)s)
                           AND rel.%(col_analytic)s = ANY(%(analytic_ids)s)
                        """,
                        rel=SQL.identifier(rel_table),
                        col_line=SQL.identifier(col_line),
                        col_analytic=SQL.identifier(col_analytic),
                        move_ids=list(move_ids),
                        analytic_ids=analytic_ids_list,
                    ))
                    return {row[0] for row in cr.fetchall()}
            except Exception:
                _logger.debug("Due report: analytic lookup via %s failed.", rel_table)

        _logger.debug(
            "Due report: M2M relation table lookup failed for analytic filter; "
            "trying analytic_distribution domain."
        )

        # --- Strategy 2: ORM domain on analytic_distribution field ---
        try:
            AML = self.env['account.move.line']
            if 'analytic_distribution' in AML._fields:
                with cr.savepoint():
                    matched_lines = AML.search([
                        ('move_id', 'in', list(move_ids)),
                        ('analytic_distribution', 'in', analytic_ids_list),
                    ])
                    return set(matched_lines.mapped('move_id').ids)
        except Exception:
            _logger.debug(
                "Due report: analytic_distribution domain search failed; "
                "falling back to Python loop."
            )

        return None  # signal to caller: fall back to Python loop

    def _filter_moves_by_analytic(self, moves, analytic_account_ids):
        """Return the subset of *moves* that touch any of *analytic_account_ids*.

        Uses ``_get_analytic_move_ids_sql`` (single SQL query) first; falls
        back to the original Python loop only if both SQL strategies fail.
        """
        if not analytic_account_ids:
            return moves

        if hasattr(analytic_account_ids, 'ids'):
            target_ids = set(int(i) for i in analytic_account_ids.ids if i)
        elif isinstance(analytic_account_ids, (list, tuple, set)):
            target_ids = set(int(i) for i in analytic_account_ids if i)
        else:
            target_ids = set()

        if not target_ids or not moves:
            return moves

        # --- Fast SQL path ---
        result = self._get_analytic_move_ids_sql(moves.ids, target_ids)
        if result is not None:
            return moves.filtered(lambda m: m.id in result)

        # --- Fallback: Python loop (kept as safety net, same logic as before) ---
        _logger.warning(
            "Due report: analytic filter falling back to Python loop for %d moves. "
            "Consider installing general_ledger_enterprise_view for better performance.",
            len(moves),
        )
        target_str_ids = set(str(i) for i in target_ids)
        filtered_move_ids = []
        for move in moves:
            match = False
            for line in move.line_ids:
                dist = line.analytic_distribution
                if dist:
                    if isinstance(dist, str):
                        try:
                            dist = json.loads(dist)
                        except Exception:
                            dist = {}
                    if isinstance(dist, dict):
                        for key in dist.keys():
                            account_ids_in_key = [x.strip() for x in str(key).split(',')]
                            if any(acc_id in target_str_ids for acc_id in account_ids_in_key):
                                match = True
                                break
                if not match and hasattr(line, 'analytic_account_id') and line.analytic_account_id:
                    if str(line.analytic_account_id.id) in target_str_ids:
                        match = True
                if match:
                    break
            if match:
                filtered_move_ids.append(move.id)
        return self.env['account.move'].browse(filtered_move_ids)

    # ------------------------------------------------------------------
    # Currency helpers
    # ------------------------------------------------------------------
    # Display rules (same idea as the Partner Ledger):
    #   * Default (no currency filter): every partner is shown in the
    #     currency of its own documents (e.g. EUR partner -> EUR).
    #     If one partner has documents in several currencies, that partner
    #     is shown in the company currency instead.
    #   * Grand totals / KPI cards use the common currency when every
    #     partner shares one; otherwise they are shown in the company
    #     currency (you cannot add EUR + SAR together).
    #   * Grand totals / KPI cards in the company currency also carry a
    #     per-transaction-currency breakdown (totals['by_currency']).
    #   * Currency filter applied: everything is converted to the chosen
    #     currency, using either the transaction-date rates or custom rates
    #     typed by the user: 1 <transaction currency> = <rate> <chosen currency>.
    # ------------------------------------------------------------------
    def _get_active_currencies(self):
        """List of active currencies for the Currency filter dropdown,
        mirroring the partner ledger's currency list endpoint."""
        currencies = self.env['res.currency'].search([('active', '=', True)], order='name asc')
        return [{
            'id': c.id,
            'name': c.name,
            'symbol': c.symbol,
            'position': c.position,
            'decimal_places': c.decimal_places,
            # units of this currency per 1 unit of the company currency;
            # used to suggest the current rate in the Custom Rate section.
            'rate': getattr(c, 'rate', 0.0) or 0.0,
        } for c in currencies]

    @staticmethod
    def _currency_dict(currency, mixed=False):
        """JSON friendly description of a res.currency record."""
        decimals = getattr(currency, 'decimal_places', 2)
        return {
            'id': currency.id,
            'name': currency.name or '',
            'symbol': currency.symbol or '',
            'position': getattr(currency, 'position', 'after') or 'after',
            'decimal_places': 2 if decimals is None else decimals,
            'mixed': mixed,
        }

    def _parse_currency_opts(self, currency_opts):
        """Return (target_currency_record | None, custom_rates | None).

        currency_opts: {
            'currency_id': int,                 # the chosen currency
            'use_transaction_rates': bool,
            'rates': {transaction_currency_id: rate},   # custom mode only
        }
        custom_rates is None in transaction-rate mode, otherwise a dict
        {transaction_currency_id: rate} meaning
        1 <transaction currency> = <rate> <chosen currency>.
        """
        if not currency_opts or not currency_opts.get('currency_id'):
            return None, None
        try:
            target = self.env['res.currency'].browse(int(currency_opts['currency_id'])).exists()
        except (TypeError, ValueError):
            return None, None
        if not target:
            return None, None
        custom_rates = None
        if not currency_opts.get('use_transaction_rates'):
            custom_rates = {}
            for key, value in (currency_opts.get('rates') or {}).items():
                try:
                    rate = float(value or 0.0)
                    currency_id = int(key)
                except (TypeError, ValueError):
                    continue
                if rate > 0:
                    custom_rates[currency_id] = rate
        return target, custom_rates

    def _line_amounts(self, move, currency, custom_rates=None, as_of_date=None, future_partials=None):
        """(bill_amount, paid, balance) of `move` expressed in `currency`.

        * As-of date logic: reconciliations with max_date > as_of_date are added back
          to residual so residual represents what was owed on as_of_date.
        * Refunds: out_refund and in_refund amounts are returned as negative numbers.
        * Custom rates / currency conversions respected.
        """
        company_currency = move.company_currency_id
        doc_currency = move.currency_id or company_currency
        is_refund = move.move_type in ('out_refund', 'in_refund')

        future_doc = 0.0
        future_co = 0.0
        if future_partials and move.id in future_partials:
            future_doc = future_partials[move.id].get('amount_currency', 0.0)
            future_co = future_partials[move.id].get('amount_company', 0.0)

        # Unsigned/raw amounts in document currency
        doc_total = move.amount_total
        raw_doc_residual = move.amount_residual + future_doc
        doc_residual = min(doc_total, max(0.0, raw_doc_residual))

        # Unsigned/raw amounts in company currency
        co_total = abs(move.amount_total_signed)
        raw_co_residual = abs(move.amount_residual_signed) + future_co
        co_residual = min(co_total, max(0.0, raw_co_residual))

        sign = -1.0 if is_refund else 1.0

        if currency == doc_currency:
            total = doc_currency.round(doc_total * sign)
            residual = doc_currency.round(doc_residual * sign)
            paid = doc_currency.round(total - residual)
            return total, paid, residual

        rate = (custom_rates or {}).get(doc_currency.id)
        if rate:
            total = currency.round(doc_total * rate * sign)
            residual = currency.round(doc_residual * rate * sign)
            paid = currency.round(total - residual)
            return total, paid, residual

        if currency == company_currency:
            total = company_currency.round(co_total * sign)
            residual = company_currency.round(co_residual * sign)
            paid = currency.round(total - residual)
            return total, paid, residual

        # Converted with transaction rate at invoice date
        rate_date = move.invoice_date or move.date or fields.Date.context_today(self)
        company = move.company_id
        conv_total = company_currency._convert(co_total, currency, company, rate_date)
        conv_residual = company_currency._convert(co_residual, currency, company, rate_date)
        total = currency.round(conv_total * sign)
        residual = currency.round(conv_residual * sign)
        paid = currency.round(total - residual)
        return total, paid, residual

    # ------------------------------------------------------------------
    # Line / group builders
    # ------------------------------------------------------------------
    def _is_overdue(self, move, as_of_date, balance=None):
        invoice_date = move.invoice_date or date.today()
        due_date = move.invoice_date_due or invoice_date
        rem_over = (as_of_date - due_date).days if (due_date and as_of_date) else 0
        if balance is not None:
            return rem_over > 0 and abs(balance) > 0.00001
        return rem_over > 0 and abs(move.amount_residual) > 0.00001

    def _get_responsible_users(self, move):
        """Users shown in the Salesman / Buyer column.

        * Customer invoices: the invoice Salesperson (invoice_user_id).
        * Vendor bills: the Buyer of the linked purchase order(s) (needs the
          purchase app), falling back to the bill's own Salesperson field.
        """
        if move.move_type in ('in_invoice', 'in_refund'):
            line_model = self.env['account.move.line']
            if 'purchase_line_id' in line_model._fields:
                orders = move.line_ids.mapped('purchase_line_id.order_id')
                if orders and 'user_id' in orders._fields:
                    buyers = orders.mapped('user_id')
                    if buyers:
                        return buyers
        return move.invoice_user_id

    def _get_responsible_map(self, moves):
        """Batch-fetch responsible users (salesperson/buyer) for a recordset of moves.
        Eliminates N+1 queries when looping over vendor bills.
        Returns: {move_id: (first_user_id or False, 'Comma separated names')}
        """
        if not moves:
            return {}

        resp_map = {}
        in_moves = moves.filtered(lambda m: m.move_type in ('in_invoice', 'in_refund'))
        out_moves = moves - in_moves

        # Customer moves: batch accessed via ORM prefetch of invoice_user_id
        for m in out_moves:
            u = m.invoice_user_id
            resp_map[m.id] = (u.id if u else False, u.name or '' if u else '')

        # Vendor bills: single SQL query to fetch buyers of linked POs
        if in_moves:
            in_ids = tuple(in_moves.ids)
            po_buyers = {}
            line_model = self.env['account.move.line']
            if 'purchase_line_id' in line_model._fields:
                try:
                    with self.env.cr.savepoint():
                        self.env.cr.execute("""
                            SELECT aml.move_id, u.id, rp.name
                              FROM account_move_line aml
                              JOIN purchase_order_line pol ON pol.id = aml.purchase_line_id
                              JOIN purchase_order po ON po.id = pol.order_id
                              JOIN res_users u ON u.id = po.user_id
                              JOIN res_partner rp ON rp.id = u.partner_id
                             WHERE aml.move_id IN %s
                             ORDER BY aml.move_id, u.id
                        """, (in_ids,))
                        for row in self.env.cr.fetchall():
                            m_id, u_id, u_name = row[0], row[1], row[2] or ''
                            if m_id not in po_buyers:
                                po_buyers[m_id] = []
                            if (u_id, u_name) not in po_buyers[m_id]:
                                po_buyers[m_id].append((u_id, u_name))
                except Exception:
                    po_buyers = {}

            # Fill in vendor bills from query or fall back to invoice_user_id
            for m in in_moves:
                buyers = po_buyers.get(m.id)
                if buyers:
                    first_uid = buyers[0][0]
                    names_str = ', '.join(b[1] for b in buyers if b[1])
                    resp_map[m.id] = (first_uid, names_str)
                else:
                    u = m.invoice_user_id
                    resp_map[m.id] = (u.id if u else False, u.name or '' if u else '')

        return resp_map

    @staticmethod
    def _clean_narration_str(raw):
        """Strip HTML tags and condense whitespace from a string."""
        if not raw:
            return ''
        try:
            clean = re.sub(r'<[^>]+>', ' ', str(raw))
            return ' '.join(clean.split())
        except Exception:
            return str(raw or '')

    @staticmethod
    def _clean_narration(move):
        """Narration as plain text (HTML tags removed)."""
        if not move.narration:
            return ''
        return DueReportWizard._clean_narration_str(move.narration)

    @staticmethod
    def _get_partner_address(partner):
        """Return a dict with email, phone and up to 2 address lines for the partner.
        Uses getattr throughout so missing optional fields (mobile, street2, zip,
        country_id) never raise AttributeError on lean Odoo CE installs."""
        parts = []
        street = getattr(partner, 'street', '') or ''
        street2 = getattr(partner, 'street2', '') or ''
        city = getattr(partner, 'city', '') or ''
        zip_code = getattr(partner, 'zip', '') or ''
        country = getattr(partner, 'country_id', None)

        if street:
            parts.append(street)
        if street2:
            parts.append(street2)
        city_parts = []
        if city:
            city_parts.append(city)
        if zip_code:
            city_parts.append(zip_code)
        if city_parts:
            parts.append(', '.join(city_parts))
        if country and getattr(country, 'name', ''):
            parts.append(country.name)

        # Limit to 2 lines for display
        address_lines = parts[:2]
        phone = getattr(partner, 'phone', '') or ''
        mobile = getattr(partner, 'mobile', '') or ''
        return {
            'email': getattr(partner, 'email', '') or '',
            'phone': phone or mobile,
            'address_line1': address_lines[0] if len(address_lines) > 0 else '',
            'address_line2': address_lines[1] if len(address_lines) > 1 else '',
        }

    def _matches_search(self, move, query, responsible_name=None, narration=None):
        """Server side twin of the on-screen search box (filteredGroups in the
        JS view): a partner name match keeps all of its documents, otherwise the
        text must appear in the voucher no., reference, LPO, narration or
        salesman. `query` must already be stripped and lower-cased."""
        if not query:
            return True
        if query in (move.partner_id.display_name or '').lower():
            return True
        if narration is None:
            narration = self._clean_narration(move)
        if responsible_name is None:
            responsible_name = ', '.join(self._get_responsible_users(move).mapped('name'))
        haystack = (
            move.name,
            move.ref,
            move.ref or move.invoice_origin,
            narration,
            responsible_name,
        )
        return any(query in str(value).lower() for value in haystack if value)

    def _compute_line(self, move, sino, as_of_date, amounts=None,
                      responsible_info=None, narration_text=None):
        """One report line. `amounts` = (bill, paid, balance) already
        expressed in the currency the line must be displayed in; when
        omitted the document's own currency is used.
        `responsible_info`: optional tuple (first_user_id, 'names') precomputed in batch.
        `narration_text`: optional pre-cleaned narration string.
        """
        invoice_date = move.invoice_date or date.today()
        due_date = move.invoice_date_due or invoice_date
        due_day = (due_date - invoice_date).days if (due_date and invoice_date) else 0
        rem_over = (as_of_date - due_date).days if (due_date and as_of_date) else 0

        if amounts is None:
            amounts = self._line_amounts(move, move.currency_id or move.company_currency_id, as_of_date=as_of_date)
        bill, paid, balance = amounts

        is_overdue = (rem_over > 0 and abs(balance) > 0.00001)

        if narration_text is None:
            narration_text = self._clean_narration(move)

        if responsible_info is not None:
            salesman_id, salesman_name = responsible_info
        else:
            responsible = self._get_responsible_users(move)
            salesman_id = responsible[:1].id if responsible else False
            salesman_name = ', '.join(responsible.mapped('name')) if responsible else ''

        # Reference or LPO
        ref_text = move.ref or move.invoice_origin or ''

        return {
            'sino': sino,
            'move_id': move.id,
            'move_type': move.move_type,
            'is_refund': move.move_type in ('out_refund', 'in_refund'),
            'vno': move.name or '',
            'inv_number': move.ref or '',
            'date': invoice_date,
            'partner': move.partner_id.display_name or '',
            'partner_name': move.partner_id.display_name or '',
            'partner_id': move.partner_id.id,
            'salesman_id': salesman_id,
            'due_day': due_day,
            'due_date': due_date,
            'rem_over_days': abs(rem_over),
            'rem_over_label': 'Over' if rem_over > 0 else 'Rem.',
            'is_overdue': is_overdue,
            'narration': narration_text,
            # Amounts are in the *display* currency of the partner group.
            'bill_amount': float(bill),
            'paid': float(paid),
            'balance': float(balance),
            'total_amount': float(bill),
            'salesman': salesman_name,
            'lpo': ref_text,
            # Currency the document was originally issued in.
            'line_currency_id': move.currency_id.id,
            'line_currency_name': move.currency_id.name or '',
            'line_currency_symbol': move.currency_id.symbol or '',
        }

    # ------------------------------------------------------------------
    # Unapplied payments / advances / credits  (NEW)
    #
    # Open items on the Receivable / Payable account that are NOT invoices
    # or credit notes (customer advances, unallocated vendor payments,
    # opening balances ...) and are not reconciled yet. Without them the
    # report would not tie out with Aged Receivable / Partner Ledger.
    # Everything here is wrapped in a savepoint: if anything fails the
    # normal report still works exactly as before.
    # ------------------------------------------------------------------
    _DOC_MOVE_TYPES = ('out_invoice', 'out_refund', 'in_invoice', 'in_refund')

    def _get_unapplied_rows(self, company, move_type, as_of_date, partner_ids=None,
                            date_from=None, analytic_active=False):
        """List of dicts (one per partner + journal entry) - see _compute_unapplied_rows."""
        if analytic_active:
            # payments carry no analytic distribution -> cannot be filtered by it
            return []
        try:
            with self.env.cr.savepoint():
                return self._compute_unapplied_rows(
                    company, move_type, as_of_date, partner_ids, date_from)
        except Exception:
            _logger.exception("Due report: could not compute unapplied payments; "
                              "report is shown without them.")
            return []

    def _compute_unapplied_rows(self, company, move_type, as_of_date, partner_ids=None,
                                date_from=None):
        cr = self.env.cr
        is_customer = move_type in ('out_invoice', 'out_refund')
        account_type = 'asset_receivable' if is_customer else 'liability_payable'
        sign = 1.0 if is_customer else -1.0
        company_currency = company.currency_id
        today = fields.Date.context_today(self)
        past_report = bool(as_of_date and as_of_date < today)

        domain = [
            ('company_id', '=', company.id),
            ('parent_state', '=', 'posted'),
            ('account_id.account_type', '=', account_type),
            ('partner_id', '!=', False),
            ('date', '<=', as_of_date),
            ('move_id.move_type', 'not in', self._DOC_MOVE_TYPES),
        ]
        if date_from:
            domain.append(('date', '>=', date_from))
        if partner_ids:
            domain.append(('partner_id', 'in', list(partner_ids)))

        # Lines still open today, plus (for a report dated in the past) lines
        # that were open on that date and were reconciled afterwards.
        open_domain = ['|', ('amount_residual', '!=', 0.0), ('amount_residual_currency', '!=', 0.0)]
        if past_report:
            # Find AML lines reconciled AFTER as_of_date — UNION ALL hits both
            # debit_move_id and credit_move_id indexes rather than an OR seq-scan.
            # When the report is limited to some partners (e.g. the partners
            # expanded on screen) only their lines are looked at, instead of
            # every reconciliation of the company.
            join_debit = join_credit = ''
            params = [company.id, as_of_date, company.id, as_of_date]
            if partner_ids:
                join_debit = ("JOIN account_move_line aml_p ON aml_p.id = apr.debit_move_id "
                              "AND aml_p.partner_id = ANY(%s)")
                join_credit = ("JOIN account_move_line aml_p ON aml_p.id = apr.credit_move_id "
                               "AND aml_p.partner_id = ANY(%s)")
                params = [list(partner_ids), company.id, as_of_date,
                          list(partner_ids), company.id, as_of_date]
            cr.execute("""
                SELECT DISTINCT sub.aml_id FROM (
                    SELECT apr.debit_move_id  AS aml_id
                      FROM account_partial_reconcile apr
                      """ + join_debit + """
                     WHERE apr.company_id = %s AND apr.max_date > %s
                    UNION ALL
                    SELECT apr.credit_move_id AS aml_id
                      FROM account_partial_reconcile apr
                      """ + join_credit + """
                     WHERE apr.company_id = %s AND apr.max_date > %s
                ) sub
            """, params)
            later_ids = [r[0] for r in cr.fetchall()]
            if later_ids:
                open_domain = ['|'] + open_domain + [('id', 'in', later_ids)]

        lines = self.env['account.move.line'].search(domain + open_domain)
        if not lines:
            return []

        future_cur, future_co = {}, {}
        if past_report:
            # Compute future reconcile amounts per line — UNION ALL for index hits.
            cr.execute("""
                SELECT aml_id,
                       SUM(future_cur) AS future_cur,
                       SUM(future_co)  AS future_co
                  FROM (
                    SELECT apr.debit_move_id AS aml_id,
                           COALESCE(NULLIF(apr.debit_amount_currency, 0.0), apr.amount)  AS future_cur,
                           apr.amount                                                     AS future_co
                      FROM account_partial_reconcile apr
                     WHERE apr.debit_move_id = ANY(%s)
                       AND apr.max_date > %s
                    UNION ALL
                    SELECT apr.credit_move_id AS aml_id,
                           -COALESCE(NULLIF(apr.credit_amount_currency, 0.0), apr.amount) AS future_cur,
                           -apr.amount                                                     AS future_co
                      FROM account_partial_reconcile apr
                     WHERE apr.credit_move_id = ANY(%s)
                       AND apr.max_date > %s
                  ) sub
                 GROUP BY aml_id
            """, (lines.ids, as_of_date, lines.ids, as_of_date))
            for line_id, f_cur, f_co in cr.fetchall():
                future_cur[line_id] = float(f_cur or 0.0)
                future_co[line_id] = float(f_co or 0.0)

        rows = {}
        for line in lines:
            line_currency = line.currency_id or company_currency
            cur_res = line.amount_residual_currency + future_cur.get(line.id, 0.0)
            co_res = line.amount_residual + future_co.get(line.id, 0.0)
            key = (line.partner_id.id, line.move_id.id)
            row = rows.get(key)
            if row is None:
                rows[key] = {
                    'partner': line.partner_id,
                    'move': line.move_id,
                    'date': line.date,
                    'currency': line_currency,
                    'cur_res': cur_res,
                    'co_res': co_res,
                    'sign': sign,
                    'company': company,
                }
                continue
            row['co_res'] += co_res
            if row['currency'] == line_currency:
                row['cur_res'] += cur_res
            else:
                # lines of one entry in different currencies -> company currency
                row['currency'] = company_currency
                row['cur_res'] = row['co_res']

        result = [
            r for r in rows.values()
            if not (company_currency.is_zero(r['co_res']) and r['currency'].is_zero(r['cur_res']))
        ]
        result.sort(key=lambda r: (r['date'] or date.min, r['move'].id))
        return result

    def _unapplied_amounts(self, row, currency, custom_rates=None):
        """(bill, paid, balance) of an unapplied row expressed in `currency`.

        balance < 0  -> credit for the partner (advance, unallocated payment):
                        shown as Paid, Bill Amount = 0, so that
                        Bill - Paid = Balance still holds.
        balance > 0  -> extra amount owed (e.g. unreconciled debit entry):
                        shown as Bill Amount.
        """
        row_currency = row['currency']
        company = row['company']
        company_currency = company.currency_id
        rate = (custom_rates or {}).get(row_currency.id)
        if currency == row_currency:
            value = row['cur_res']
        elif rate:
            value = row['cur_res'] * rate
        elif currency == company_currency:
            value = row['co_res']
        else:
            value = company_currency._convert(
                row['co_res'], currency, company, row['date'] or fields.Date.context_today(self))
        balance = currency.round(value * row['sign'])
        if balance < 0:
            return 0.0, currency.round(-balance), balance
        return balance, 0.0, balance

    def _compute_unapplied_line(self, row, sino, as_of_date, amounts):
        """Report line (same keys as _compute_line) for an unapplied row."""
        move = row['move']
        partner = row['partner']
        bill, paid, balance = amounts
        line_date = row['date'] or as_of_date
        rem_over = (as_of_date - line_date).days if (as_of_date and line_date) else 0
        is_overdue = rem_over > 0 and abs(balance) > 0.00001
        ref_text = move.ref or ''
        return {
            'sino': sino,
            'move_id': move.id,
            'vno': move.name or '',
            'inv_number': ref_text,
            'date': line_date,
            'partner': partner.display_name or '',
            'partner_name': partner.display_name or '',
            'partner_id': partner.id,
            'salesman_id': False,
            'due_day': 0,
            'due_date': line_date,
            'rem_over_days': abs(rem_over),
            'rem_over_label': 'Over' if rem_over > 0 else 'Rem.',
            'is_overdue': is_overdue,
            'narration': self._clean_narration(move) or ref_text,
            'bill_amount': float(bill),
            'paid': float(paid),
            'balance': float(balance),
            'total_amount': float(bill),
            'salesman': '',
            'lpo': ref_text,
            'line_currency_id': row['currency'].id,
            'line_currency_name': row['currency'].name or '',
            'line_currency_symbol': row['currency'].symbol or '',
            'move_type': move.move_type,
            'is_refund': False,
            'is_unapplied': True,
            'paid_by_text': '',
        }

    def _matches_unapplied_search(self, row, query):
        """Same idea as _matches_search, for unapplied rows."""
        if not query:
            return True
        move = row['move']
        haystack = (row['partner'].display_name, move.name, move.ref)
        return any(query in str(value).lower() for value in haystack if value)

    # ------------------------------------------------------------------
    # "Paid by" explanation under each document  (NEW, display only)
    # ------------------------------------------------------------------
    def _get_paid_by_map(self, move_ids, as_of_date):
        """{move_id: [(counterpart document name, amount in document currency)]}
        for the reconciliations dated on / before as_of_date. Any error ->
        empty map (the report simply shows no 'Paid by' text)."""
        if not move_ids:
            return {}
        try:
            with self.env.cr.savepoint():
                self.env.cr.execute("""
                    SELECT inv.move_id,
                           COALESCE(NULLIF(om.name, ''), om.ref, ''),
                           SUM(CASE WHEN inv.id = apr.debit_move_id
                                    THEN COALESCE(NULLIF(apr.debit_amount_currency, 0.0), apr.amount)
                                    ELSE COALESCE(NULLIF(apr.credit_amount_currency, 0.0), apr.amount)
                               END)
                      FROM account_partial_reconcile apr
                      JOIN account_move_line inv ON inv.id IN (apr.debit_move_id, apr.credit_move_id)
                      JOIN account_move_line oth ON oth.id = CASE WHEN inv.id = apr.debit_move_id
                                                                  THEN apr.credit_move_id
                                                                  ELSE apr.debit_move_id END
                      JOIN account_move om ON om.id = oth.move_id
                     WHERE inv.move_id = ANY(%s)
                       AND apr.max_date <= %s
                       AND oth.move_id <> inv.move_id
                       AND NOT EXISTS (SELECT 1 FROM account_partial_reconcile ex
                                        WHERE ex.exchange_move_id = oth.move_id)
                     GROUP BY inv.move_id, om.id, om.name, om.ref
                     ORDER BY 2
                """, (list(move_ids), as_of_date))
                result = {}
                for move_id, name, amount in self.env.cr.fetchall():
                    result.setdefault(move_id, []).append((name, float(amount or 0.0)))
                return result
        except Exception:
            _logger.exception("Due report: could not compute the 'Paid by' text.")
            return {}

    @staticmethod
    def _format_paid_by(items, is_refund=False):
        if not items:
            return ''
        label = 'Applied to' if is_refund else 'Paid by'
        return "%s: %s" % (label, ', '.join("%s (%s)" % (n, format(a, ',.2f')) for n, a in items if n))

    def _build_groups(self, moves, today, company, due_filter='all',
                      currency_opts=None, iso_dates=False, search_query=None,
                      as_of_date=None, future_partials=None, only_due=False,
                      unapplied=None, _totals_currency_override=None,
                      mode='full', _maps=None):
        """Group `moves` per partner and express every amount in the right
        currency (see the rules at the top of this section).

        mode:
          'full'    - every group carries ALL its lines, grand totals included
                      (PDF / Excel / old on-screen behaviour).
          'summary' - every group carries only its HEADER: subtotals, counts and
                      the upcoming / overdue buckets (in the partner currency and
                      in the grand-total currency). No line dict, narration,
                      buyer or "paid by" text is built, so the payload and the
                      memory stay small. The on-screen view uses it and loads the
                      lines of a partner only when that partner is expanded.
          'lines'   - groups carry their lines only (used by
                      get_due_report_partner_lines). Grand totals are not
                      converted because the caller ignores them.

        Returns (groups, totals, totals_currency_dict).
        """
        if as_of_date is None:
            as_of_date = today
        if future_partials is None:
            future_partials = self._get_future_reconciled_amounts(moves, as_of_date)

        summary = (mode == 'summary')
        lines_mode = (mode == 'lines')
        target, custom_rates = self._parse_currency_opts(currency_opts)
        company_currency = company.currency_id
        Move = self.env['account.move']

        moves = moves.sorted(key=lambda m: (
            m.partner_id.display_name or '', m.partner_id.id,
            m.invoice_date or date.min, m.id,
        ))

        query = (search_query or '').strip().lower()

        # Buyer / narration are only needed to print lines or to search them.
        if _maps is not None:
            responsible_map, narration_map = _maps
        elif summary and not query:
            responsible_map, narration_map = {}, {}
        else:
            responsible_map = self._get_responsible_map(moves)
            narration_map = {m.id: self._clean_narration_str(m.narration) for m in moves}

        # 1. Bucket the moves per partner (optionally filtered by the search text)
        move_buckets = {}
        for move in moves:
            if query:
                resp_info = responsible_map.get(move.id)
                salesman_str = resp_info[1] if resp_info else ''
                narr_str = narration_map.get(move.id, '')
                if not self._matches_search(move, query, responsible_name=salesman_str, narration=narr_str):
                    continue
            move_buckets.setdefault(move.partner_id.id, []).append(move.id)

        # 1b. Unapplied payments / advances / unreconciled credits (extra lines)
        unapplied_by_partner = {}
        for row in (unapplied or []):
            if query and not self._matches_unapplied_search(row, query):
                continue
            unapplied_by_partner.setdefault(row['partner'].id, []).append(row)
        paid_by_map = {} if summary else self._get_paid_by_map(moves.ids, as_of_date)

        # 2. Decide the display currency of every partner
        prepared = []
        for move_ids in move_buckets.values():
            pmoves = Move.browse(move_ids)
            doc_currencies = pmoves.mapped('currency_id')
            if target:
                group_currency = target
            elif len(doc_currencies) == 1:
                group_currency = doc_currencies[0]
            else:
                group_currency = company_currency
            prepared.append((pmoves, group_currency, len(doc_currencies) > 1 and not target,
                             pmoves[0].partner_id))

        # Partners that have ONLY unapplied items (e.g. a pure advance payment)
        for pid, urows in unapplied_by_partner.items():
            if pid in move_buckets:
                continue
            cur_ids = {r['currency'].id for r in urows}
            if target:
                group_currency = target
            elif len(cur_ids) == 1:
                group_currency = urows[0]['currency']
            else:
                group_currency = company_currency
            prepared.append((Move.browse(), group_currency, len(cur_ids) > 1 and not target,
                             urows[0]['partner']))
        prepared.sort(key=lambda p: (p[3].display_name or '', p[3].id))

        # 3. Currency used for KPI cards / grand totals
        if target:
            totals_currency, mixed = target, False
        elif _totals_currency_override is not None:
            totals_currency, mixed = _totals_currency_override, False
        else:
            distinct_ids = {gc.id for _pm, gc, _mx, _pt in prepared}
            if len(distinct_ids) > 1:
                totals_currency, mixed = company_currency, True
            elif prepared:
                totals_currency, mixed = prepared[0][1], False
            else:
                totals_currency, mixed = company_currency, False

        totals = {
            'bill_amount': 0.0,
            'paid': 0.0,
            'balance': 0.0,
            'total_amount': 0.0,
            'invoice_count': 0,
            'partner_count': 0,
            'overdue_balance': 0.0,
            'overdue_count': 0,
            'upcoming_balance': 0.0,
            'upcoming_count': 0,
            'remaining_balance': 0.0,
            'remaining_count': 0,
            # Per transaction currency breakdown; only filled when the
            # grand totals had to be converted to the company currency.
            'by_currency': [],
        }
        by_currency = {}

        def new_bucket():
            # t_* = same figures expressed in the grand-total currency
            return {'count': 0, 'bill': 0.0, 'paid': 0.0, 'balance': 0.0,
                    't_bill': 0.0, 't_paid': 0.0, 't_balance': 0.0}

        def account(group, is_overdue, amounts, t_amounts):
            """Single place where one document / unapplied row is added to the
            partner subtotals, the upcoming / overdue buckets and the grand
            totals (so the on-screen header, the lines, PDF and Excel can
            never drift apart)."""
            bill, paid, balance = amounts
            t_bill, t_paid, t_balance = t_amounts
            group['subtotal_bill_amount'] += bill
            group['subtotal_paid'] += paid
            group['subtotal_balance'] += balance
            group['subtotal_total_amount'] += bill
            group['count'] += 1
            bucket = group['buckets']['overdue' if is_overdue else 'upcoming']
            bucket['count'] += 1
            bucket['bill'] += bill
            bucket['paid'] += paid
            bucket['balance'] += balance
            bucket['t_bill'] += t_bill
            bucket['t_paid'] += t_paid
            bucket['t_balance'] += t_balance
            totals['bill_amount'] += t_bill
            totals['total_amount'] += t_bill
            totals['paid'] += t_paid
            totals['balance'] += t_balance
            totals['invoice_count'] += 1
            if is_overdue:
                group['subtotal_overdue'] += balance
                totals['overdue_balance'] += t_balance
                totals['overdue_count'] += 1
            else:
                group['subtotal_upcoming'] += balance
                totals['upcoming_balance'] += t_balance
                totals['upcoming_count'] += 1
                totals['remaining_balance'] += t_balance
                totals['remaining_count'] += 1

        def iso(value):
            return value.isoformat() if hasattr(value, 'isoformat') else str(value or '')

        # 4. Build the groups
        groups = []
        for pmoves, group_currency, mixed_docs, partner in prepared:
            phone = getattr(partner, 'phone', '') or getattr(partner, 'mobile', '') or ''
            group = {
                'partner_id': partner.id,
                'partner_name': partner.display_name or getattr(partner, 'name', '') or 'Unknown Partner',
                'partner_phone': phone,
                'partner_address': self._get_partner_address(partner),
                'currency': self._currency_dict(group_currency),
                'currency_id': group_currency.id,
                'mixed_docs': mixed_docs,
                'lines': [],
                # False in 'summary' mode: the client asks for the lines when
                # the partner is expanded.
                'lines_loaded': not summary,
                'buckets': {'upcoming': new_bucket(), 'overdue': new_bucket()},
                'subtotal_bill_amount': 0.0,
                'subtotal_paid': 0.0,
                'subtotal_balance': 0.0,
                'subtotal_upcoming': 0.0,
                'subtotal_overdue': 0.0,
                'subtotal_total_amount': 0.0,
                'count': 0,
            }
            same_currency = (group_currency == totals_currency)

            sino = 1
            for move in pmoves:
                amounts = self._line_amounts(
                    move, group_currency, custom_rates,
                    as_of_date=as_of_date, future_partials=future_partials
                )
                bill, paid, balance = amounts

                if only_due and group_currency.is_zero(balance):
                    continue

                is_overdue = self._is_overdue(move, as_of_date, balance)
                if due_filter == 'upcoming' and is_overdue:
                    continue
                if due_filter == 'overdue' and not is_overdue:
                    continue

                if same_currency or lines_mode:
                    t_amounts = amounts
                else:
                    # Grand totals are kept in the totals currency
                    t_amounts = self._line_amounts(
                        move, totals_currency, custom_rates,
                        as_of_date=as_of_date, future_partials=future_partials
                    )

                if not summary:
                    line = self._compute_line(
                        move, sino, as_of_date, amounts=amounts,
                        responsible_info=responsible_map.get(move.id),
                        narration_text=narration_map.get(move.id, '')
                    )
                    line['currency_id'] = group_currency.id
                    line['paid_by_text'] = self._format_paid_by(
                        paid_by_map.get(move.id), move.move_type in ('out_refund', 'in_refund'))
                    if t_amounts is not amounts:
                        line['t_bill_amount'] = float(t_amounts[0])
                        line['t_paid'] = float(t_amounts[1])
                        line['t_balance'] = float(t_amounts[2])
                    if iso_dates:
                        line['date'] = iso(line['date'])
                        line['due_date'] = iso(line['due_date'])
                    group['lines'].append(line)

                account(group, is_overdue, amounts, t_amounts)
                sino += 1

            # Unapplied payments / advances / credits of this partner
            for row in unapplied_by_partner.get(partner.id, []):
                amounts = self._unapplied_amounts(row, group_currency, custom_rates)
                bill, paid, balance = amounts

                line_date = row['date'] or as_of_date
                rem_over = (as_of_date - line_date).days if (as_of_date and line_date) else 0
                is_overdue = rem_over > 0 and abs(balance) > 0.00001
                if due_filter == 'upcoming' and is_overdue:
                    continue
                if due_filter == 'overdue' and not is_overdue:
                    continue

                if same_currency or lines_mode:
                    t_amounts = amounts
                else:
                    t_amounts = self._unapplied_amounts(row, totals_currency, custom_rates)

                if not summary:
                    line = self._compute_unapplied_line(row, sino, as_of_date, amounts)
                    line['currency_id'] = group_currency.id
                    if t_amounts is not amounts:
                        line['t_bill_amount'] = float(t_amounts[0])
                        line['t_paid'] = float(t_amounts[1])
                        line['t_balance'] = float(t_amounts[2])
                    if iso_dates:
                        line['date'] = iso(line['date'])
                        line['due_date'] = iso(line['due_date'])
                    group['lines'].append(line)

                account(group, is_overdue, amounts, t_amounts)
                sino += 1

            if group['count']:
                # Round accumulated subtotals to eliminate float drift (0.01 issues).
                cr_fn = group_currency.round
                for key in ('subtotal_bill_amount', 'subtotal_paid', 'subtotal_balance',
                            'subtotal_total_amount', 'subtotal_upcoming', 'subtotal_overdue'):
                    group[key] = cr_fn(group[key])
                tc_fn = totals_currency.round
                for bucket in group['buckets'].values():
                    bucket['bill'] = cr_fn(bucket['bill'])
                    bucket['paid'] = cr_fn(bucket['paid'])
                    bucket['balance'] = cr_fn(bucket['balance'])
                    bucket['t_bill'] = tc_fn(bucket['t_bill'])
                    bucket['t_paid'] = tc_fn(bucket['t_paid'])
                    bucket['t_balance'] = tc_fn(bucket['t_balance'])

                groups.append(group)
                totals['partner_count'] += 1

                if mixed:
                    entry = by_currency.setdefault(group_currency.id, {
                        'currency': group['currency'],
                        'bill_amount': 0.0,
                        'paid': 0.0,
                        'balance': 0.0,
                        'upcoming_balance': 0.0,
                        'overdue_balance': 0.0,
                    })
                    entry['bill_amount'] += group['subtotal_bill_amount']
                    entry['paid'] += group['subtotal_paid']
                    entry['balance'] += group['subtotal_balance']
                    entry['upcoming_balance'] += group['subtotal_upcoming']
                    entry['overdue_balance'] += group['subtotal_overdue']

        # The grand-total currency was chosen BEFORE the lines were built. If it
        # fell back to the company currency only because of partners that ended
        # up with no visible lines, but the partners actually shown all share
        # one currency, rebuild once with that currency (e.g. EUR partner only).
        if mixed and not target and _totals_currency_override is None and not lines_mode:
            shown_currency_ids = {g['currency_id'] for g in groups}
            if len(shown_currency_ids) == 1:
                return self._build_groups(
                    moves, today, company, due_filter=due_filter,
                    currency_opts=currency_opts, iso_dates=iso_dates,
                    search_query=search_query, as_of_date=as_of_date,
                    future_partials=future_partials, only_due=only_due,
                    unapplied=unapplied,
                    _totals_currency_override=self.env['res.currency'].browse(
                        next(iter(shown_currency_ids))),
                    mode=mode, _maps=(responsible_map, narration_map),
                )

        if mixed:
            totals['by_currency'] = sorted(by_currency.values(), key=lambda e: e['currency']['name'])

        # Round grand totals in the totals currency to eliminate float accumulation.
        tc_round = totals_currency.round
        for key in ('bill_amount', 'paid', 'balance', 'total_amount',
                    'overdue_balance', 'upcoming_balance', 'remaining_balance'):
            totals[key] = tc_round(totals[key])

        return groups, totals, self._currency_dict(totals_currency, mixed=mixed)

    def get_report_lines(self):
        """Flat list of lines (all partners together) - used by the
        on-screen View, which keeps every column."""
        self.ensure_one()
        as_of_date = self.date_to or fields.Date.context_today(self)
        moves = self._get_moves(as_of_date=as_of_date).sorted(key=lambda m: (m.invoice_date or date.min, m.id))
        future_partials = self._get_future_reconciled_amounts(moves, as_of_date)
        lines = []
        totals = {
            'bill_amount': 0.0,
            'paid': 0.0,
            'balance': 0.0,
            'total_amount': 0.0,
            'upcoming_balance': 0.0,
            'overdue_balance': 0.0,
            'upcoming_count': 0,
            'overdue_count': 0,
        }

        sino = 1
        responsible_map = self._get_responsible_map(moves)
        narration_map = {m.id: self._clean_narration_str(m.narration) for m in moves}

        for move in moves:
            amounts = self._line_amounts(
                move, move.currency_id or move.company_currency_id,
                as_of_date=as_of_date, future_partials=future_partials
            )
            bill, paid, balance = amounts
            if self.only_due and (move.currency_id or move.company_currency_id).is_zero(balance):
                continue

            line = self._compute_line(
                move, sino, as_of_date, amounts=amounts,
                responsible_info=responsible_map.get(move.id),
                narration_text=narration_map.get(move.id, '')
            )
            lines.append(line)
            totals['bill_amount'] += line['bill_amount']
            totals['paid'] += line['paid']
            totals['balance'] += line['balance']
            totals['total_amount'] += line['total_amount']
            if line['is_overdue']:
                totals['overdue_balance'] += line['balance']
                totals['overdue_count'] += 1
            else:
                totals['upcoming_balance'] += line['balance']
                totals['upcoming_count'] += 1
            sino += 1

        return lines, totals

    def get_grouped_report(self, currency_opts=None):
        """Lines grouped by partner (one table per customer/vendor) -
        used by the printed PDF and the Excel export. Sl No restarts at 1
        within each group.

        Returns (groups, totals, totals_currency_dict)."""
        self.ensure_one()
        as_of_date = self.date_to or fields.Date.context_today(self)
        moves = self._get_moves(as_of_date=as_of_date)
        future_partials = self._get_future_reconciled_amounts(moves, as_of_date)
        unapplied = self._get_unapplied_rows(
            self.company_id, self.move_type, as_of_date,
            partner_ids=self.partner_ids.ids, date_from=self.date_from,
            analytic_active=bool(self.analytic_account_ids),
        )
        return self._build_groups(
            moves, as_of_date, self.company_id,
            due_filter=self.due_filter, currency_opts=currency_opts,
            search_query=self.search_query,
            as_of_date=as_of_date, future_partials=future_partials,
            only_due=self.only_due, unapplied=unapplied,
        )

    def get_grouped_lines(self):
        """Backward compatible wrapper: (groups, grand_total_balance, grand_totals)."""
        groups, totals, _currency = self.get_grouped_report()
        return groups, totals['balance'], totals

    def _get_pdf_render_values(self, currency_opts=None):
        """Values shared by the customer / vendor PDF parsers."""
        self.ensure_one()
        groups, totals, totals_currency = self.get_grouped_report(currency_opts)
        Currency = self.env['res.currency']
        for group in groups:
            # QWeb's monetary widget needs a real res.currency record.
            group['currency_rec'] = Currency.browse(group['currency']['id'])
        for entry in totals.get('by_currency', []):
            entry['currency_rec'] = Currency.browse(entry['currency']['id'])
        analytic_names = ", ".join(self.analytic_account_ids.mapped('display_name')) if self.analytic_account_ids else False
        return {
            'groups': groups,
            'grand_total_balance': totals['balance'],
            'grand_totals': totals,
            'show_grand_total': self.show_grand_total,
            'show_address': self.show_address,
            'company': self.company_id,
            'display_currency': Currency.browse(totals_currency['id']),
            'totals_mixed': totals_currency['mixed'],
            'date_from': self.date_from,
            'date_to': self.date_to,
            'analytic_names': analytic_names,
        }

    @api.model
    def export_xlsx(self, options=None, **kwargs):
        """Export Due Report data to Excel (XLSX) format."""
        import io
        import base64
        import xlsxwriter

        if options is None:
            options = kwargs.get('options') or kwargs or {}

        wizard = self.create({
            'move_type': options.get('move_type', 'out_invoice'),
            'date_from': options.get('date_from') or False,
            'date_to': options.get('date_to') or False,
            'partner_ids': [(6, 0, options.get('partner_ids', []))],
            'analytic_account_ids': [(6, 0, options.get('analytic_account_ids', []))],
            'only_due': options.get('only_due', True),
            'due_filter': options.get('due_filter', 'all'),
            'show_grand_total': options.get('show_grand_total', True),
            'show_address': options.get('show_address', False),
            'search_query': options.get('search_query') or False,
            'company_id': options.get('company_id') or self.env.company.id,
        })

        # Every partner is exported in its own transaction currency unless a
        # currency filter is applied (same rules as the on-screen view).
        currency_opts = options.get('currency_opts') or False
        groups, grand_totals, totals_currency = wizard.get_grouped_report(currency_opts)
        if not groups:
            raise UserError('No records found for the selected criteria.')
        grand_total_balance = grand_totals.get('balance', 0.0)
        company = wizard.company_id
        currency_symbol = totals_currency.get('symbol') or ''

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        is_customer = (wizard.move_type == 'out_invoice')
        sheet_name = 'Customer Due Report' if is_customer else 'Vendor Due Report'
        worksheet = workbook.add_worksheet(sheet_name[:31])

        # Formats
        title_fmt = workbook.add_format({
            'bold': True, 'font_size': 14, 'align': 'left', 'valign': 'vcenter',
            'font_color': '#1e293b'
        })
        subtitle_fmt = workbook.add_format({
            'bold': True, 'font_size': 11, 'align': 'left', 'valign': 'vcenter',
            'font_color': '#475569'
        })
        date_range_fmt = workbook.add_format({
            'font_size': 10, 'align': 'left', 'valign': 'vcenter', 'font_color': '#64748b'
        })
        partner_header_fmt = workbook.add_format({
            'bold': True, 'font_size': 11, 'bg_color': '#f8fafc',
            'top': 1, 'bottom': 1, 'border_color': '#cbd5e1'
        })
        partner_subtotal_info_fmt = workbook.add_format({
            'font_size': 9.5, 'align': 'right', 'bg_color': '#f8fafc',
            'top': 1, 'bottom': 1, 'border_color': '#cbd5e1'
        })
        table_header_fmt = workbook.add_format({
            'bold': True, 'font_size': 9.5, 'bg_color': '#9db4c4',
            'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': '#94a3b8'
        })
        table_header_right_fmt = workbook.add_format({
            'bold': True, 'font_size': 9.5, 'bg_color': '#9db4c4',
            'align': 'right', 'valign': 'vcenter', 'border': 1, 'border_color': '#94a3b8'
        })
        data_text_fmt = workbook.add_format({
            'font_size': 9.5, 'align': 'left', 'valign': 'vcenter', 'border': 1, 'border_color': '#e2e8f0'
        })
        data_center_fmt = workbook.add_format({
            'font_size': 9.5, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': '#e2e8f0'
        })
        data_date_fmt = workbook.add_format({
            'font_size': 9.5, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': '#e2e8f0',
            'num_format': 'yyyy-mm-dd'
        })
        data_num_fmt = workbook.add_format({
            'font_size': 9.5, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'border_color': '#e2e8f0',
            'num_format': '#,##0.00'
        })
        data_num_bold_fmt = workbook.add_format({
            'bold': True, 'font_size': 9.5, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'border_color': '#e2e8f0',
            'num_format': '#,##0.00'
        })
        subtotal_label_fmt = workbook.add_format({
            'bold': True, 'font_size': 9.5, 'align': 'right', 'bg_color': '#e2e2e2',
            'border': 1, 'border_color': '#94a3b8'
        })
        subtotal_num_fmt = workbook.add_format({
            'bold': True, 'font_size': 9.5, 'align': 'right', 'bg_color': '#e2e2e2',
            'border': 1, 'border_color': '#94a3b8', 'num_format': '#,##0.00'
        })
        # Grand total block: plain left aligned bold lines, no background
        gt_title_fmt = workbook.add_format({
            'bold': True, 'font_size': 11, 'align': 'left', 'valign': 'vcenter',
        })
        gt_note_fmt = workbook.add_format({
            'font_size': 9.5, 'align': 'left', 'valign': 'vcenter', 'font_color': '#64748b',
        })
        gt_line_fmt = workbook.add_format({
            'bold': True, 'font_size': 10.5, 'align': 'left', 'valign': 'vcenter',
        })
        gt_currency_fmt = workbook.add_format({
            'font_size': 9.5, 'align': 'left', 'valign': 'vcenter',
        })
        partner_address_fmt = workbook.add_format({
            'font_size': 9, 'align': 'left', 'valign': 'vcenter',
            'font_color': '#475569', 'bg_color': '#f8fafc',
            'bottom': 1, 'border_color': '#cbd5e1',
            'italic': True,
        })

        # Report Header
        row = 0
        worksheet.write(row, 0, company.name or 'Company', title_fmt)
        row += 1
        worksheet.write(row, 0, 'Customers Due Report' if is_customer else 'Supplier Due Report', subtitle_fmt)
        row += 1
        if wizard.date_from:
            date_str = f"{wizard.date_from} To {wizard.date_to or 'End'}"
        else:
            date_str = f"As of {wizard.date_to or 'Today'}"
        worksheet.write(row, 0, f"Period: {date_str}", date_range_fmt)
        if wizard.analytic_account_ids:
            analytic_names = ", ".join(wizard.analytic_account_ids.mapped('name'))
            row += 1
            worksheet.write(row, 0, f"Analytic: {analytic_names}", date_range_fmt)
        row += 1

        headers = [
            'SlNo', 'Date', 'VNo', 'Due Day', 'Due Date', 'Status / Days',
            'Bill Amount', 'Paid', 'Balance Due',
            'PO/Reference #' if is_customer else 'Vendor Ref #'
        ]

        for group in groups:
            row += 1
            # Partner summary header
            group_symbol = group['currency'].get('symbol') or ''
            summary_info = (
                f"Upcoming Due: {group['subtotal_upcoming']:,.2f} {group_symbol}  |  "
                f"Overdue: {group['subtotal_overdue']:,.2f} {group_symbol}  |  "
                f"Total Balance: {group['subtotal_balance']:,.2f} {group_symbol}"
            )
            partner_title = f"{group['partner_name']} ({group['currency'].get('name')})"
            worksheet.merge_range(row, 0, row, 4, partner_title, partner_header_fmt)
            worksheet.merge_range(row, 5, row, len(headers) - 1, summary_info, partner_subtotal_info_fmt)
            row += 1

            # Partner Address row (only when show_address is enabled)
            if wizard.show_address and group.get('partner_address'):
                addr = group['partner_address']
                parts = []
                if addr.get('email'):
                    parts.append(f"✉ {addr['email']}")
                if addr.get('phone'):
                    parts.append(f"✆ {addr['phone']}")
                if addr.get('address_line1'):
                    parts.append(f"⌂ {addr['address_line1']}")
                if addr.get('address_line2'):
                    parts.append(addr['address_line2'])
                if parts:
                    address_text = '   |   '.join(parts)
                    worksheet.merge_range(row, 0, row, len(headers) - 1, address_text, partner_address_fmt)
                    row += 1

            # Table Header
            for col_idx, h in enumerate(headers):
                if h in ('Bill Amount', 'Paid', 'Balance Due'):
                    worksheet.write(row, col_idx, h, table_header_right_fmt)
                else:
                    worksheet.write(row, col_idx, h, table_header_fmt)
            row += 1

            # Lines
            for line in group['lines']:
                status_text = 'Unapplied' if line.get('is_unapplied') else f"{line['rem_over_days']} {'Over' if line['is_overdue'] else 'Rem.'}"
                worksheet.write(row, 0, line['sino'], data_center_fmt)
                worksheet.write(row, 1, str(line['date'] or ''), data_date_fmt)
                vno_text = line['vno'] or ''
                if line.get('is_refund'):
                    vno_text += ' (Refund)'
                elif line.get('is_unapplied'):
                    vno_text += ' (Advance / Unapplied)'
                worksheet.write(row, 2, vno_text, data_text_fmt)
                worksheet.write(row, 3, line['due_day'] or 0, data_center_fmt)
                worksheet.write(row, 4, str(line['due_date'] or ''), data_date_fmt)
                worksheet.write(row, 5, status_text, data_center_fmt)
                worksheet.write(row, 6, line['bill_amount'] or 0.0, data_num_fmt)
                worksheet.write(row, 7, line['paid'] or 0.0, data_num_fmt)
                worksheet.write(row, 8, line['balance'] or 0.0, data_num_bold_fmt)
                worksheet.write(row, 9, line['lpo'] if is_customer else (line['inv_number'] or line['lpo']), data_text_fmt)
                row += 1

            # Partner Subtotal row
            worksheet.merge_range(row, 0, row, 5, 'Partner Total:', subtotal_label_fmt)
            worksheet.write(row, 6, group['subtotal_bill_amount'], subtotal_num_fmt)
            worksheet.write(row, 7, group['subtotal_paid'], subtotal_num_fmt)
            worksheet.write(row, 8, group['subtotal_balance'], subtotal_num_fmt)
            worksheet.write(row, 9, '', subtotal_label_fmt)
            row += 1

        # Grand Total Summary - plain left aligned lines (no background)
        if wizard.show_grand_total and grand_totals and groups:
            row += 2
            worksheet.merge_range(row, 0, row, 9, 'Grand Total Summary', gt_title_fmt)
            row += 1
            worksheet.merge_range(
                row, 0, row, 9,
                f"Across {grand_totals['partner_count']} partners and {grand_totals['invoice_count']} documents",
                gt_note_fmt,
            )
            for label, key in (
                ('Total Invoiced', 'bill_amount'),
                ('Total Paid', 'paid'),
                ('Upcoming Due', 'upcoming_balance'),
                ('Overdue', 'overdue_balance'),
                ('Grand Total', 'balance'),
            ):
                row += 1
                worksheet.merge_range(
                    row, 0, row, 9,
                    f"{label}: {grand_totals[key]:,.2f} {currency_symbol}",
                    gt_line_fmt,
                )

        # Set Column Widths
        col_widths = [8, 13, 20, 10, 13, 14, 16, 16, 16, 22]
        for c_idx, width in enumerate(col_widths):
            worksheet.set_column(c_idx, c_idx, width)

        workbook.close()
        output.seek(0)
        file_content = base64.b64encode(output.read()).decode('utf-8')
        output.close()

        file_prefix = 'Customer_Due_Report' if is_customer else 'Vendor_Due_Report'
        filename = f"{file_prefix}_{fields.Date.today()}.xlsx"

        return {
            'filename': filename,
            'filecontent': file_content,
        }

    # ------------------------------------------------------------------
    # Option parsing shared by the on-screen APIs
    # ------------------------------------------------------------------
    _VALID_MOVE_TYPES = ('out_invoice', 'out_refund', 'in_invoice', 'in_refund')
    # Hard cap of partners whose lines can be loaded in ONE call (the screen
    # never asks for more than a page of partners at once).
    _MAX_LAZY_PARTNERS = 200

    @staticmethod
    def _clean_date_option(value):
        value = str(value).strip() if value else ''
        return value if value not in ('false', 'False', 'null', 'None', 'undefined', '') else False

    @staticmethod
    def _clean_id_list(values):
        if not isinstance(values, (list, tuple, set)):
            return []
        result = []
        for value in values:
            if isinstance(value, bool):
                continue
            try:
                result.append(int(value))
            except (TypeError, ValueError):
                continue
        return result

    def _parse_report_options(self, options):
        """Validate and normalise the `options` dict sent by the OWL view."""
        options = options or {}

        company = self.env.company
        company_id = options.get('company_id')
        if company_id and str(company_id).isdigit():
            company = self.env['res.company'].browse(int(company_id)).exists()
        if not company or company not in self.env.user.company_ids:
            raise AccessError(_("You are not allowed to access this company."))

        raw_move_type = options.get('move_type', 'out_invoice')
        if raw_move_type not in self._VALID_MOVE_TYPES:
            raw_move_type = 'out_invoice'
        move_types = self._get_move_types(raw_move_type)
        is_customer = ('out_invoice' in move_types)

        today = fields.Date.context_today(self)
        if isinstance(today, str):
            today = fields.Date.from_string(today)
        date_to = self._clean_date_option(options.get('date_to'))
        as_of_date = fields.Date.from_string(date_to) if date_to else today

        return {
            'company': company,
            'move_types': move_types,
            'is_customer': is_customer,
            'report_move_type': 'out_invoice' if is_customer else 'in_invoice',
            'date_from': self._clean_date_option(options.get('date_from')),
            'date_to': date_to,
            'as_of_date': as_of_date,
            'partner_ids': self._clean_id_list(options.get('partner_ids')),
            'analytic_ids': self._clean_id_list(options.get('analytic_account_ids')),
            'only_due': options.get('only_due', True),
            'currency_opts': options.get('currency_opts') or False,
            'search_query': (options.get('search_query') or '').strip(),
        }

    # ------------------------------------------------------------------
    # Actions & OWL View APIs
    # ------------------------------------------------------------------
    @api.model
    def get_due_report_data(self, options=None, **kwargs):
        """Returns structured data for the interactive OWL Due Report View.

        options['lazy_lines'] = True  -> every partner group carries only its
            header (subtotals, counts, upcoming / overdue buckets) and
            `lines_loaded = False`. The lines are fetched per partner with
            get_due_report_partner_lines() when the partner is expanded.
        options['include_lists'] = False -> the partner / analytic / currency
            selector lists and the logo are not sent again (the screen already
            has them), e.g. when only the search text changed.
        """
        if options is None:
            options = kwargs.get('options') or kwargs or {}

        opts = self._parse_report_options(options)
        company = opts['company']
        as_of_date = opts['as_of_date']
        lazy_lines = bool(options.get('lazy_lines'))
        include_lists = options.get('include_lists', True)
        due_filter = options.get('due_filter', 'all')
        show_grand_total = options.get('show_grand_total', True)
        show_address = options.get('show_address', False)

        moves = self._fetch_report_moves(
            company=company,
            move_types=opts['move_types'],
            date_from=opts['date_from'],
            date_to=opts['date_to'],
            partner_ids=opts['partner_ids'],
            only_due=opts['only_due'],
            as_of_date=as_of_date,
            analytic_account_ids=opts['analytic_ids'],
        )

        future_partials = self._get_future_reconciled_amounts(moves, as_of_date)

        # Currencies the listed documents were issued in (needed by the
        # Custom Rate section of the Currency filter).
        transaction_currencies = [
            self._currency_dict(c) for c in sorted(moves.mapped('currency_id'), key=lambda c: c.name or '')
        ]

        # The due status filter (all / upcoming / overdue) is applied on the
        # client for the on-screen view (every group carries upcoming / overdue
        # buckets), so build with 'all' here.
        unapplied = self._get_unapplied_rows(
            company, opts['report_move_type'], as_of_date,
            partner_ids=opts['partner_ids'],
            date_from=opts['date_from'],
            analytic_active=bool(opts['analytic_ids']),
        )
        groups, totals, totals_currency = self._build_groups(
            moves, as_of_date, company,
            due_filter='all', currency_opts=opts['currency_opts'], iso_dates=True,
            search_query=opts['search_query'],
            as_of_date=as_of_date, future_partials=future_partials,
            only_due=opts['only_due'], unapplied=unapplied,
            mode='summary' if lazy_lines else 'full',
        )

        result = {
            'groups': groups,
            'totals': totals,
            'lazy_lines': lazy_lines,
            # Currency of the KPI cards / grand totals. Each group also
            # carries its own `currency` (the partner's transaction currency).
            'currency': totals_currency,
            'company_currency': self._currency_dict(company.currency_id),
            'transaction_currencies': transaction_currencies,
            'company': {
                'id': company.id,
                'name': company.name,
                'logo': False,
            },
            'move_type': opts['report_move_type'],
            'report_title': 'Customer Due Report' if opts['is_customer'] else 'Vendor Due Report',
            'date_from': options.get('date_from') or False,
            'date_to': options.get('date_to') or False,
            'analytic_account_ids': opts['analytic_ids'],
            'only_due': opts['only_due'],
            'due_filter': due_filter,
            'show_grand_total': show_grand_total,
            'show_address': show_address,
        }
        if include_lists:
            result.update(self._get_selector_lists(company))
        return result

    def _get_selector_lists(self, company):
        """Partner / analytic / currency lists for the selector dropdowns and
        the company logo. Static for a given company, so the screen asks for
        them only once."""
        # Partners list for selector dropdown (order by SQL column 'name' or 'id')
        partner_domain = [('company_id', 'in', [False, company.id])]
        try:
            partner_records = self.env['res.partner'].search_read(
                partner_domain, ['id', 'display_name', 'name'], limit=300, order='name asc'
            )
        except Exception:
            try:
                partner_records = self.env['res.partner'].search_read(
                    [], ['id', 'display_name', 'name'], limit=300, order='name asc'
                )
            except Exception:
                partner_records = []

        for p in partner_records:
            if not p.get('display_name'):
                p['display_name'] = p.get('name') or ''
        partner_records.sort(key=lambda p: (p.get('display_name') or '').lower())

        # Analytic Accounts list for selector dropdown (order by SQL column 'name' or 'id')
        analytic_domain = [('company_id', 'in', [False, company.id])]
        try:
            analytics_records = self.env['account.analytic.account'].search_read(
                analytic_domain, ['id', 'display_name', 'name'], limit=200, order='name asc'
            )
        except Exception:
            try:
                analytics_records = self.env['account.analytic.account'].search_read(
                    [], ['id', 'name'], limit=200, order='name asc'
                )
            except Exception:
                analytics_records = []

        for a in analytics_records:
            if not a.get('display_name'):
                a['display_name'] = a.get('name') or ''
        analytics_records.sort(key=lambda a: (a.get('display_name') or '').lower())

        logo_b64 = False
        if company.logo:
            try:
                import base64
                if isinstance(company.logo, bytes):
                    logo_b64 = base64.b64encode(company.logo).decode('utf-8')
                elif isinstance(company.logo, str):
                    logo_b64 = company.logo
            except Exception:
                logo_b64 = False

        return {
            'currencies': self._get_active_currencies(),
            'partners_list': partner_records,
            'analytics_list': analytics_records,
            'company': {
                'id': company.id,
                'name': company.name,
                'logo': logo_b64,
            },
        }

    @api.model
    def get_due_report_partner_lines(self, options=None, partner_ids=None, **kwargs):
        """Lines of a few partners (the ones expanded on screen).

        Uses exactly the same options / pipeline as get_due_report_data()
        (same as-of date logic, currency rules, search text, unapplied
        payments), restricted to `partner_ids`, so the lines always add up to
        the partner header the screen already shows.

        Returns {str(partner_id): {'lines': [...], 'count': n}}.
        """
        if options is None:
            options = kwargs.get('options') or {}
        wanted = self._clean_id_list(partner_ids)
        if not wanted:
            return {}
        if len(wanted) > self._MAX_LAZY_PARTNERS:
            raise UserError(
                "Too many partners requested at once (%d, maximum %d). "
                "Please expand fewer partners." % (len(wanted), self._MAX_LAZY_PARTNERS)
            )

        opts = self._parse_report_options(options)
        if opts['partner_ids']:
            selected = set(opts['partner_ids'])
            wanted = [pid for pid in wanted if pid in selected]
            if not wanted:
                return {}
        company = opts['company']
        as_of_date = opts['as_of_date']

        moves = self._fetch_report_moves(
            company=company,
            move_types=opts['move_types'],
            date_from=opts['date_from'],
            date_to=opts['date_to'],
            partner_ids=wanted,
            only_due=opts['only_due'],
            as_of_date=as_of_date,
            analytic_account_ids=opts['analytic_ids'],
        )
        future_partials = self._get_future_reconciled_amounts(moves, as_of_date)
        unapplied = self._get_unapplied_rows(
            company, opts['report_move_type'], as_of_date,
            partner_ids=wanted,
            date_from=opts['date_from'],
            analytic_active=bool(opts['analytic_ids']),
        )
        groups, _totals, _currency = self._build_groups(
            moves, as_of_date, company,
            due_filter='all', currency_opts=opts['currency_opts'], iso_dates=True,
            search_query=opts['search_query'],
            as_of_date=as_of_date, future_partials=future_partials,
            only_due=opts['only_due'], unapplied=unapplied,
            mode='lines',
        )
        return {
            str(group['partner_id']): {'lines': group['lines'], 'count': group['count']}
            for group in groups
        }

    @api.model
    def get_pdf_report_action(self, options=None, **kwargs):
        """Trigger PDF report printing from the OWL view."""
        if options is None:
            options = kwargs.get('options') or kwargs or {}
        wizard = self.create({
            'move_type': options.get('move_type', 'out_invoice'),
            'date_from': options.get('date_from') or False,
            'date_to': options.get('date_to') or False,
            'partner_ids': [(6, 0, options.get('partner_ids', []))],
            'analytic_account_ids': [(6, 0, options.get('analytic_account_ids', []))],
            'only_due': options.get('only_due', True),
            'due_filter': options.get('due_filter', 'all'),
            'show_grand_total': options.get('show_grand_total', True),
            'show_address': options.get('show_address', False),
            'search_query': options.get('search_query') or False,
            'company_id': options.get('company_id') or self.env.company.id,
        })
        currency_opts = options.get('currency_opts') or False
        return wizard.action_print_report(currency_opts=currency_opts)


    def action_print_report(self, currency_opts=None):
        self.ensure_one()
        groups, _totals, _currency = self.get_grouped_report(currency_opts)
        if not groups:
            raise UserError('No records found for the selected criteria.')

        data = {'wizard_id': self.id, 'currency_opts': currency_opts or False}
        if self.move_type == 'out_invoice':
            report_ref = 'custom_due_reports.action_report_customer_due'
        else:
            report_ref = 'custom_due_reports.action_report_vendor_due'
        return self.env.ref(report_ref).report_action(self, data=data)

    def action_view_report(self):
        """Show the interactive OWL Due Report view on screen."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'custom_due_reports.DueReportView',
            'name': 'Customer Due Report' if self.move_type == 'out_invoice' else 'Vendor Due Report',
            'params': {
                'move_type': self.move_type,
                'date_from': self.date_from.isoformat() if self.date_from else False,
                'date_to': self.date_to.isoformat() if self.date_to else False,
                'partner_ids': self.partner_ids.ids,
                'analytic_account_ids': self.analytic_account_ids.ids,
                'only_due': self.only_due,
                'due_filter': self.due_filter or 'all',
                'show_grand_total': self.show_grand_total,
                'company_id': self.company_id.id,
            },
            'context': dict(self.env.context, active_id=self.id),
        }