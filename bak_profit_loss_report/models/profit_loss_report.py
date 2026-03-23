# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ProfitLossReport(models.TransientModel):
    _name = 'bak.profit.loss.report'
    _description = 'Profit & Loss Inline Report'

    date_from = fields.Date(
        string='Start Date',
        default=lambda self: fields.Date.today().replace(day=1, month=1))
    date_to = fields.Date(
        string='End Date',
        default=fields.Date.context_today)
    target_move = fields.Selection([
        ('posted', 'All Posted Entries'),
        ('all',    'All Entries'),
    ], string='Target Moves', default='posted')
    display_debit_credit = fields.Boolean(
        string='Display Debit/Credit Columns', default=False)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company)
    comparison_date_from = fields.Date(string='Comparison Start Date')
    comparison_date_to   = fields.Date(string='Comparison End Date')
    enable_comparison    = fields.Boolean(string='Enable Comparison', default=False)

    # ------------------------------------------------------------------
    # Schema introspection helpers
    # ------------------------------------------------------------------
    def _get_columns(self, table):
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
    # SQL fragment builders (same pattern as balance sheet)
    # ------------------------------------------------------------------
    def _build_code_fragment(self):
        aa_cols = self._get_columns('account_account')
        if 'code' in aa_cols:
            return "aa.code", "aa.code", ""
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
        _logger.warning('bak_profit_loss: no code column/table found, using id as code')
        return "CAST(aa.id AS VARCHAR) AS code", "aa.id", ""

    def _build_name_fragment(self):
        cr = self.env.cr
        cr.execute("""
            SELECT data_type FROM information_schema.columns
            WHERE table_name = 'account_account' AND column_name = 'name'
        """)
        row = cr.fetchone()
        if row and 'json' in (row[0] or '').lower():
            lang = self.env.lang or self.env.user.lang or 'en_US'
            lang_pg = lang.replace('-', '_')
            return (
                f"COALESCE(aa.name->>'{lang_pg}', "
                f"aa.name->>'en_US', "
                f"aa.name->>(SELECT code FROM res_lang WHERE active=TRUE LIMIT 1), "
                f"aa.name::text) AS name"
            )
        return "aa.name"

    def _build_type_fragment(self):
        aa_cols = self._get_columns('account_account')
        if 'account_type' in aa_cols:
            return "aa.account_type", ""
        if 'user_type_id' in aa_cols:
            return ("aat.type AS account_type",
                    "LEFT JOIN account_account_type aat ON aat.id = aa.user_type_id")
        return "'' AS account_type", ""

    def _build_company_fragment(self):
        aa_cols = self._get_columns('account_account')
        cid = self.company_id.id
        if 'company_id' in aa_cols:
            return '', 'AND aa.company_id = %s', [cid]
        for tbl in ('account_account_res_company_rel', 'account_account_company_rel'):
            if self._table_exists(tbl):
                tbl_cols = self._get_columns(tbl)
                co_col   = next((c for c in tbl_cols if 'company' in c), None)
                ac_col   = next((c for c in tbl_cols if 'account' in c), None)
                if co_col and ac_col:
                    join = f"""JOIN {tbl} crel
                        ON crel.{ac_col} = aa.id AND crel.{co_col} = %s"""
                    return join, '', [cid]
        _logger.warning('bak_profit_loss: no company filter possible, showing all accounts')
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
            row[0]: {
                'debit':   float(row[1]),
                'credit':  float(row[2]),
                'balance': float(row[3]),
            }
            for row in cr.fetchall()
        }

    # ------------------------------------------------------------------
    # P&L section mapping
    # income   → Revenue (credit-normal → show as positive when credit > debit)
    # expense  → Expenses (debit-normal → show as positive when debit > credit)
    # ------------------------------------------------------------------
    #
    # P&L structure:
    #   REVENUE
    #     - Sales Revenue          (income)
    #     - Other Income           (income_other)
    #   COST OF REVENUE
    #     - Direct Costs           (expense_direct_cost)
    #   GROSS PROFIT  = Revenue - Cost of Revenue
    #   OPERATING EXPENSES
    #     - General Expenses       (expense)
    #     - Depreciation           (expense_depreciation)
    #   NET PROFIT = Gross Profit - Operating Expenses
    # ------------------------------------------------------------------
    def _get_pl_groups(self):
        cr        = self.env.cr
        date_from = self.date_from
        date_to   = self.date_to or fields.Date.today()

        balances      = self._compute_account_balances(date_from, date_to)
        comp_balances = {}
        if self.enable_comparison and self.comparison_date_to:
            comp_balances = self._compute_account_balances(
                self.comparison_date_from, self.comparison_date_to)

        # Build SQL fragments
        code_select, code_order, code_join         = self._build_code_fragment()
        name_select                                = self._build_name_fragment()
        type_select, type_join                     = self._build_type_fragment()
        company_join, company_where, co_params     = self._build_company_fragment()
        depr_clause                                = self._build_deprecated_fragment()

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

        # section → subsection label
        SECTION_MAP = {
            'income':                  ('revenue',  'Sales Revenue'),
            'income_other':            ('revenue',  'Other Income'),
            'expense_direct_cost':     ('cogs',     'Cost of Revenue'),
            'expense':                 ('opex',     'General & Admin Expenses'),
            'expense_depreciation':    ('opex',     'Depreciation & Amortisation'),
        }

        sections = {
            'revenue': {},
            'cogs':    {},
            'opex':    {},
        }

        for acc_id, code, name, account_type in rows:
            if account_type not in SECTION_MAP:
                continue
            section, subsection = SECTION_MAP[account_type]

            bal      = balances.get(acc_id, {})
            comp_bal = comp_balances.get(acc_id, {})

            # Income accounts: credit-normal → positive balance means credit > debit
            # We want to show income as positive number so negate the raw balance
            # (odoo balance = debit - credit, so income balance is negative → negate)
            if section == 'revenue':
                balance      = -bal.get('balance', 0.0)
                comp_balance = -comp_bal.get('balance', 0.0)
            else:
                # Expense: debit-normal, balance is positive already
                balance      = bal.get('balance', 0.0)
                comp_balance = comp_bal.get('balance', 0.0)

            if balance == 0.0 and comp_balance == 0.0:
                continue

            # Handle JSONB name
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
    # Public: full report dict
    # ------------------------------------------------------------------
    def get_report_data(self):
        sections = self._get_pl_groups()

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

        rev_subs,  total_revenue, comp_revenue = _build(sections['revenue'])
        cogs_subs, total_cogs,    comp_cogs    = _build(sections['cogs'])
        opex_subs, total_opex,    comp_opex    = _build(sections['opex'])

        gross_profit      = total_revenue - total_cogs
        comp_gross_profit = comp_revenue  - comp_cogs
        net_profit        = gross_profit  - total_opex
        comp_net_profit   = comp_gross_profit - comp_opex

        currency = self.company_id.currency_id

        return {
            'date_from':                  str(self.date_from) if self.date_from else None,
            'date_to':                    str(self.date_to or fields.Date.today()),
            'target_move':                self.target_move,
            'display_debit_credit':       self.display_debit_credit,
            'enable_comparison':          self.enable_comparison,
            'comparison_date_from':       str(self.comparison_date_from) if self.comparison_date_from else None,
            'comparison_date_to':         str(self.comparison_date_to)   if self.comparison_date_to   else None,
            'company_name':               self.company_id.name,
            'currency_symbol':            currency.symbol,
            'currency_position':          currency.position,
            # Revenue
            'revenue':                    rev_subs,
            'total_revenue':              total_revenue,
            'comp_total_revenue':         comp_revenue,
            # COGS
            'cogs':                       cogs_subs,
            'total_cogs':                 total_cogs,
            'comp_total_cogs':            comp_cogs,
            # Gross Profit
            'gross_profit':               gross_profit,
            'comp_gross_profit':          comp_gross_profit,
            # Operating Expenses
            'opex':                       opex_subs,
            'total_opex':                 total_opex,
            'comp_total_opex':            comp_opex,
            # Net Profit
            'net_profit':                 net_profit,
            'comp_net_profit':            comp_net_profit,
        }
