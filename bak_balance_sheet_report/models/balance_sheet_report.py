# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class BalanceSheetInlineReport(models.TransientModel):
    _name = 'bak.balance.sheet.report'
    _description = 'Balance Sheet Inline Report'

    date_from = fields.Date(string='Start Date')
    date_to   = fields.Date(string='End Date', default=fields.Date.context_today)
    target_move = fields.Selection([
        ('posted', 'All Posted Entries'),
        ('all',    'All Entries'),
    ], string='Target Moves', default='posted')
    display_debit_credit = fields.Boolean(
        string='Display Debit/Credit Columns', default=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company)
    comparison_date_from = fields.Date(string='Comparison Start Date')
    comparison_date_to   = fields.Date(string='Comparison End Date')
    enable_comparison    = fields.Boolean(string='Enable Comparison', default=False)

    # ------------------------------------------------------------------
    # Helper: detect actual columns on account_account
    # Odoo 19 removed 'code' from account_account — codes moved to
    # a separate account.account.code model / account_account_code table
    # ------------------------------------------------------------------
    def _get_account_table_columns(self):
        """Return set of column names that actually exist on account_account."""
        cr = self.env.cr
        cr.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'account_account'
        """)
        return {row[0] for row in cr.fetchall()}

    def _get_code_join(self, columns):
        """
        Returns (extra_select, extra_join) to get the account code.
        - Odoo <= 17:  'code' column exists directly on account_account
        - Odoo 18/19:  codes are in account_account_code table,
                       joined via account_account_id; we pick the
                       most recent / active code entry.
        """
        if 'code' in columns:
            return "aa.code AS code", ""

        # Check if account_account_code table exists
        cr = self.env.cr
        cr.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_name = 'account_account_code'
        """)
        if cr.fetchone():
            return (
                "COALESCE(aac.code, '') AS code",
                """LEFT JOIN (
                    SELECT DISTINCT ON (account_id) account_id, code
                    FROM account_account_code
                    ORDER BY account_id, date_stop DESC NULLS FIRST, id DESC
                ) aac ON aac.account_id = aa.id"""
            )

        # Fallback: no code available
        return "'?' AS code", ""

    # ------------------------------------------------------------------
    # Helper: detect company filter method
    # ------------------------------------------------------------------
    def _account_company_filter(self):
        """
        Returns (join_sql, where_sql, params) to filter account_account
        by current company. Auto-detects schema version.
        """
        cr = self.env.cr
        columns = self._get_account_table_columns()

        if 'company_id' in columns:
            return '', 'AND aa.company_id = %s', [self.company_id.id]

        # Many2many relation table
        cr.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_name IN (
                'account_account_res_company_rel',
                'account_account_company_rel',
                'res_company_account_account_rel'
            ) LIMIT 1
        """)
        rel = cr.fetchone()
        if rel:
            rel_table = rel[0]
            cr.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = %s
            """, [rel_table])
            cols = [r[0] for r in cr.fetchall()]
            company_col = next((c for c in cols if 'company' in c), None)
            account_col = next((c for c in cols if 'account' in c), None)
            if company_col and account_col:
                join_sql = f"""
                    JOIN {rel_table} crel
                      ON crel.{account_col} = aa.id
                      AND crel.{company_col} = %s"""
                return join_sql, '', [self.company_id.id]

        _logger.warning('bak_balance_sheet: cannot filter accounts by company, showing all.')
        return '', '', []

    # ------------------------------------------------------------------
    # Core: compute balances from account_move_line
    # ------------------------------------------------------------------
    def _compute_account_balances(self, date_from=None, date_to=None):
        cr = self.env.cr
        params = [self.company_id.id]

        state_clause    = "AND am.state = 'posted'" if self.target_move == 'posted' else ''
        date_from_clause = ''
        date_to_clause   = ''

        if date_from:
            date_from_clause = 'AND aml.date >= %s'
            params.append(date_from)
        if date_to:
            date_to_clause = 'AND aml.date <= %s'
            params.append(date_to)

        cr.execute(f"""
            SELECT
                aml.account_id,
                COALESCE(SUM(aml.debit),   0) AS debit,
                COALESCE(SUM(aml.credit),  0) AS credit,
                COALESCE(SUM(aml.balance), 0) AS balance
            FROM account_move_line aml
            JOIN account_move am ON am.id = aml.move_id
            WHERE aml.company_id = %s
              {state_clause}
              {date_from_clause}
              {date_to_clause}
            GROUP BY aml.account_id
        """, params)

        return {
            row[0]: {
                'debit':   float(row[1]),
                'credit':  float(row[2]),
                'balance': float(row[3]),
            }
            for row in cr.fetchall()
        }

    # ------------------------------------------------------------------
    # Core: load accounts and group into sections
    # ------------------------------------------------------------------
    def _get_account_groups(self):
        cr        = self.env.cr
        date_to   = self.date_to or fields.Date.today()
        date_from = self.date_from

        balances      = self._compute_account_balances(date_from, date_to)
        comp_balances = {}
        if self.enable_comparison and self.comparison_date_to:
            comp_balances = self._compute_account_balances(
                self.comparison_date_from, self.comparison_date_to)

        # Detect available columns
        columns = self._get_account_table_columns()
        code_select, code_join = self._get_code_join(columns)
        company_join, company_where, company_params = self._account_company_filter()

        # Detect account_type column (could be 'account_type' or 'user_type_id')
        if 'account_type' in columns:
            type_select = 'aa.account_type'
        elif 'user_type_id' in columns:
            # Odoo < 16 used user_type_id -> join to account.account.type
            type_select = 'aat.type AS account_type'
        else:
            type_select = "'' AS account_type"

        # Detect name: 'name' is always present but may be jsonb in v19
        # Use a safe cast
        cr.execute("""
            SELECT data_type FROM information_schema.columns
            WHERE table_name = 'account_account' AND column_name = 'name'
        """)
        name_type = cr.fetchone()
        if name_type and 'json' in (name_type[0] or '').lower():
            # JSONB multilang field — extract current language
            name_select = "COALESCE(aa.name->>'en_US', aa.name::text) AS name"
        else:
            name_select = "aa.name"

        # deprecated column check
        depr_col = 'aa.deprecated' if 'deprecated' in columns else 'FALSE'

        user_type_join = ''
        if 'user_type_id' in columns:
            user_type_join = 'LEFT JOIN account_account_type aat ON aat.id = aa.user_type_id'

        cr.execute(f"""
            SELECT
                aa.id,
                {code_select},
                {name_select},
                {type_select}
            FROM account_account aa
            {code_join}
            {company_join}
            {user_type_join}
            WHERE ({depr_col} IS NULL OR {depr_col} = FALSE)
              {company_where}
            ORDER BY {code_select}
        """, company_params)

        rows = cr.fetchall()

        SECTION_MAP = {
            'asset_cash':            ('assets',      'Bank and Cash Accounts'),
            'asset_receivable':      ('assets',      'Receivables'),
            'asset_current':         ('assets',      'Current Assets'),
            'asset_prepayments':     ('assets',      'Prepayments'),
            'asset_fixed':           ('assets',      'Plus Fixed Assets'),
            'asset_non_current':     ('assets',      'Plus Non-current Assets'),
            'liability_payable':     ('liabilities', 'Payables'),
            'liability_current':     ('liabilities', 'Current Liabilities'),
            'liability_credit_card': ('liabilities', 'Current Liabilities'),
            'liability_non_current': ('liabilities', 'Plus Non-current Liabilities'),
            'equity_unaffected':     ('equity',      'Unallocated Earnings'),
            'equity':                ('equity',      'Retained Earnings'),
            # Legacy Odoo < 16 type names
            'receivable':            ('assets',      'Receivables'),
            'payable':               ('liabilities', 'Payables'),
            'bank':                  ('assets',      'Bank and Cash Accounts'),
            'cash':                  ('assets',      'Bank and Cash Accounts'),
            'asset':                 ('assets',      'Current Assets'),
            'equity':                ('equity',      'Retained Earnings'),
            'liability':             ('liabilities', 'Current Liabilities'),
        }

        sections = {'assets': {}, 'liabilities': {}, 'equity': {}}

        for acc_id, code, name, account_type in rows:
            if account_type not in SECTION_MAP:
                continue
            section, subsection = SECTION_MAP[account_type]

            bal      = balances.get(acc_id, {})
            comp_bal = comp_balances.get(acc_id, {})
            balance      = bal.get('balance', 0.0)
            comp_balance = comp_bal.get('balance', 0.0)

            if balance == 0.0 and comp_balance == 0.0:
                continue

            # Handle jsonb name
            if isinstance(name, dict):
                name = name.get('en_US') or next(iter(name.values()), '')

            sections[section].setdefault(subsection, []).append({
                'id':           acc_id,
                'code':         code or '',
                'name':         name or '',
                'debit':        bal.get('debit', 0.0),
                'credit':       bal.get('credit', 0.0),
                'balance':      balance,
                'comp_balance': comp_balance,
            })

        return sections

    # ------------------------------------------------------------------
    # Public: full report dict for controller / JS
    # ------------------------------------------------------------------
    def get_report_data(self):
        sections = self._get_account_groups()

        def _build(section_data):
            result     = []
            grand      = 0.0
            grand_comp = 0.0
            for name, rows in section_data.items():
                sub_total = sum(r['balance']      for r in rows)
                sub_comp  = sum(r['comp_balance'] for r in rows)
                grand      += sub_total
                grand_comp += sub_comp
                result.append({
                    'name':          name,
                    'rows':          rows,
                    'subtotal':      sub_total,
                    'comp_subtotal': sub_comp,
                })
            return result, grand, grand_comp

        assets_subs, total_assets, comp_total_assets   = _build(sections['assets'])
        liab_subs,   total_liab,   comp_total_liab     = _build(sections['liabilities'])
        equity_subs, total_equity, comp_total_equity   = _build(sections['equity'])

        currency = self.company_id.currency_id

        return {
            'date_to':                       str(self.date_to or fields.Date.today()),
            'date_from':                     str(self.date_from) if self.date_from else None,
            'target_move':                   self.target_move,
            'display_debit_credit':          self.display_debit_credit,
            'enable_comparison':             self.enable_comparison,
            'comparison_date_to':            str(self.comparison_date_to) if self.comparison_date_to else None,
            'company_name':                  self.company_id.name,
            'currency_symbol':               currency.symbol,
            'currency_position':             currency.position,
            'assets':                        assets_subs,
            'total_assets':                  total_assets,
            'comp_total_assets':             comp_total_assets,
            'liabilities':                   liab_subs,
            'total_liabilities':             total_liab,
            'comp_total_liabilities':        comp_total_liab,
            'equity':                        equity_subs,
            'total_equity':                  total_equity,
            'comp_total_equity':             comp_total_equity,
            'total_liabilities_equity':      total_liab + total_equity,
            'comp_total_liabilities_equity': comp_total_liab + comp_total_equity,
        }
