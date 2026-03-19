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
    # Schema introspection helpers (cached per request)
    # ------------------------------------------------------------------
    def _get_columns(self, table):
        """Return set of column names for a given table."""
        cr = self.env.cr
        cr.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = %s
        """, [table])
        return {r[0] for r in cr.fetchall()}

    def _table_exists(self, table):
        cr = self.env.cr
        cr.execute("""
            SELECT 1 FROM information_schema.tables
            WHERE table_name = %s LIMIT 1
        """, [table])
        return bool(cr.fetchone())

    # ------------------------------------------------------------------
    # Build SELECT fragments for code, name, account_type
    # Returns (code_select, code_order, code_join)
    # code_select  = SQL expression for SELECT list (includes alias if needed)
    # code_order   = SQL expression safe for ORDER BY (no alias)
    # code_join    = extra JOIN clause or ''
    # ------------------------------------------------------------------
    def _build_code_fragment(self):
        aa_cols = self._get_columns('account_account')

        if 'code' in aa_cols:
            # Standard Odoo <= 17 — code column on account_account
            return "aa.code", "aa.code", ""

        # Odoo 18/19 — code moved to account_account_code table
        # Try different possible table / column names
        for tbl in ('account_account_code', 'account_code'):
            if self._table_exists(tbl):
                tbl_cols = self._get_columns(tbl)
                acc_col  = next((c for c in tbl_cols if 'account' in c and c != 'account_type'), None)
                code_col = 'code' if 'code' in tbl_cols else None
                if acc_col and code_col:
                    join = f"""LEFT JOIN (
                        SELECT DISTINCT ON (account_id) account_id, code
                        FROM {tbl}
                        ORDER BY account_id, date_stop DESC NULLS FIRST, id DESC
                    ) aac ON aac.{acc_col} = aa.id"""
                    return "COALESCE(aac.code, '') AS code", "COALESCE(aac.code, '')", join

        # Fallback: no code table found — use aa.id cast as text
        _logger.warning('bak_balance_sheet: no code column/table found, using id as code')
        return "CAST(aa.id AS VARCHAR) AS code", "aa.id", ""

    def _build_name_fragment(self):
        """Return SQL expression for account name, handling JSONB."""
        cr = self.env.cr
        cr.execute("""
            SELECT data_type FROM information_schema.columns
            WHERE table_name = 'account_account' AND column_name = 'name'
        """)
        row = cr.fetchone()
        if row and 'json' in (row[0] or '').lower():
            # JSONB multilang — try to get the installed language
            lang = self.env.lang or self.env.user.lang or 'en_US'
            lang_pg = lang.replace('-', '_')  # e.g. ar_001 or en_US
            return (
                f"COALESCE(aa.name->>'{lang_pg}', "
                f"aa.name->>'en_US', "
                f"aa.name->>(SELECT code FROM res_lang WHERE active=TRUE LIMIT 1), "
                f"aa.name::text) AS name"
            )
        return "aa.name"

    def _build_type_fragment(self):
        """Return (type_select, type_join) for account_type."""
        aa_cols = self._get_columns('account_account')
        if 'account_type' in aa_cols:
            return "aa.account_type", ""
        if 'user_type_id' in aa_cols:
            return ("aat.type AS account_type",
                    "LEFT JOIN account_account_type aat ON aat.id = aa.user_type_id")
        return "'' AS account_type", ""

    def _build_company_fragment(self):
        """Return (join_sql, where_sql, params) to filter by company."""
        aa_cols = self._get_columns('account_account')
        cid = self.company_id.id

        if 'company_id' in aa_cols:
            return '', 'AND aa.company_id = %s', [cid]

        # Many2many relation table
        for tbl in ('account_account_res_company_rel', 'account_account_company_rel'):
            if self._table_exists(tbl):
                tbl_cols = self._get_columns(tbl)
                co_col   = next((c for c in tbl_cols if 'company' in c), None)
                ac_col   = next((c for c in tbl_cols if 'account' in c), None)
                if co_col and ac_col:
                    join = f"""JOIN {tbl} crel
                        ON crel.{ac_col} = aa.id AND crel.{co_col} = %s"""
                    return join, '', [cid]

        _logger.warning('bak_balance_sheet: no company filter possible, showing all accounts')
        return '', '', []

    def _build_deprecated_fragment(self):
        aa_cols = self._get_columns('account_account')
        if 'deprecated' in aa_cols:
            return '(aa.deprecated IS NULL OR aa.deprecated = FALSE)'
        return 'TRUE'

    # ------------------------------------------------------------------
    # Core: compute balances from account_move_line
    # ------------------------------------------------------------------
    def _compute_account_balances(self, date_from=None, date_to=None):
        cr     = self.env.cr
        params = [self.company_id.id]

        state_sql    = "AND am.state = 'posted'" if self.target_move == 'posted' else ''
        datefrom_sql = ''
        dateto_sql   = ''

        if date_from:
            datefrom_sql = 'AND aml.date >= %s'
            params.append(date_from)
        if date_to:
            dateto_sql = 'AND aml.date <= %s'
            params.append(date_to)

        cr.execute(f"""
            SELECT
                aml.account_id,
                COALESCE(SUM(aml.debit),   0),
                COALESCE(SUM(aml.credit),  0),
                COALESCE(SUM(aml.balance), 0)
            FROM account_move_line aml
            JOIN account_move am ON am.id = aml.move_id
            WHERE aml.company_id = %s
              {state_sql}
              {datefrom_sql}
              {dateto_sql}
            GROUP BY aml.account_id
        """, params)

        return {
            row[0]: {'debit': float(row[1]), 'credit': float(row[2]), 'balance': float(row[3])}
            for row in cr.fetchall()
        }

    # ------------------------------------------------------------------
    # Core: load accounts and group into balance sheet sections
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

        # Build all SQL fragments
        code_select, code_order, code_join   = self._build_code_fragment()
        name_select                          = self._build_name_fragment()
        type_select, type_join               = self._build_type_fragment()
        company_join, company_where, co_params = self._build_company_fragment()
        depr_clause                          = self._build_deprecated_fragment()

        cr.execute(f"""
            SELECT
                aa.id,
                {code_select},
                {name_select},
                {type_select}
            FROM account_account aa
            {code_join}
            {company_join}
            {type_join}
            WHERE {depr_clause}
              {company_where}
            ORDER BY {code_order}
        """, co_params)

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

            # Handle JSONB name returned as Python dict
            if isinstance(name, dict):
                lang = self.env.lang or 'en_US'
                name = name.get(lang) or name.get('en_US') or next(iter(name.values()), '')

            sections[section].setdefault(subsection, []).append({
                'id':           acc_id,
                'code':         str(code or ''),
                'name':         str(name or ''),
                'debit':        bal.get('debit',  0.0),
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

        assets_subs, total_assets, comp_total_assets = _build(sections['assets'])
        liab_subs,   total_liab,   comp_total_liab   = _build(sections['liabilities'])
        equity_subs, total_equity, comp_total_equity = _build(sections['equity'])

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
