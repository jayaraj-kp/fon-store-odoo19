# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools import date_utils
from datetime import date, datetime
import json


class BalanceSheetInlineReport(models.TransientModel):
    _name = 'bak.balance.sheet.report'
    _description = 'Balance Sheet Inline Report'

    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date', default=fields.Date.context_today)
    target_move = fields.Selection([
        ('posted', 'All Posted Entries'),
        ('all', 'All Entries'),
    ], string='Target Moves', default='posted')
    display_debit_credit = fields.Boolean(
        string='Display Debit/Credit Columns', default=True
    )
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company
    )
    comparison_date_from = fields.Date(string='Comparison Start Date')
    comparison_date_to = fields.Date(string='Comparison End Date')
    enable_comparison = fields.Boolean(string='Enable Comparison', default=False)

    # ------------------------------------------------------------------
    # Action opener – called from menu
    # ------------------------------------------------------------------
    def action_open_report(self):
        """Open the balance sheet inline report view."""
        wizard = self.create({})
        return {
            'type': 'ir.actions.act_url',
            'url': '/bak/balance_sheet?wizard_id=%d' % wizard.id,
            'target': 'self',
        }

    # ------------------------------------------------------------------
    # Core data builder
    # ------------------------------------------------------------------
    def _get_account_move_lines_domain(self, date_from=None, date_to=None):
        domain = [('company_id', '=', self.company_id.id)]
        if self.target_move == 'posted':
            domain += [('move_id.state', '=', 'posted')]
        if date_from:
            domain += [('date', '>=', date_from)]
        if date_to:
            domain += [('date', '<=', date_to)]
        return domain

    def _compute_account_balances(self, date_from=None, date_to=None):
        """Return dict {account_id: {'debit': x, 'credit': x, 'balance': x}}"""
        domain = self._get_account_move_lines_domain(date_from, date_to)
        lines = self.env['account.move.line'].read_group(
            domain,
            ['account_id', 'debit', 'credit', 'balance'],
            ['account_id'],
        )
        result = {}
        for line in lines:
            acc_id = line['account_id'][0]
            result[acc_id] = {
                'debit': line['debit'],
                'credit': line['credit'],
                'balance': line['balance'],
            }
        return result

    def _get_account_groups(self):
        """
        Returns grouped account data structured for balance sheet rendering.
        Sections: ASSETS, LIABILITIES, EQUITY
        """
        AccountGroup = self.env['account.group']
        Account = self.env['account.account']

        date_to = self.date_to or fields.Date.today()
        date_from = self.date_from

        balances = self._compute_account_balances(date_from, date_to)

        comp_balances = {}
        if self.enable_comparison and self.comparison_date_to:
            comp_balances = self._compute_account_balances(
                self.comparison_date_from, self.comparison_date_to
            )

        # Map Odoo account types to balance sheet sections
        ASSET_TYPES = {
            'asset_cash', 'asset_receivable', 'asset_current',
            'asset_prepayments', 'asset_fixed', 'asset_non_current'
        }
        LIABILITY_TYPES = {
            'liability_payable', 'liability_current',
            'liability_non_current', 'liability_credit_card'
        }
        EQUITY_TYPES = {'equity', 'equity_unaffected'}

        def _section_of(acc):
            t = acc.account_type
            if t in ASSET_TYPES:
                return 'assets'
            if t in LIABILITY_TYPES:
                return 'liabilities'
            if t in EQUITY_TYPES:
                return 'equity'
            return None

        def _subsection_of(acc):
            t = acc.account_type
            mapping = {
                'asset_cash': 'Bank and Cash Accounts',
                'asset_receivable': 'Receivables',
                'asset_current': 'Current Assets',
                'asset_prepayments': 'Prepayments',
                'asset_fixed': 'Plus Fixed Assets',
                'asset_non_current': 'Plus Non-current Assets',
                'liability_payable': 'Payables',
                'liability_current': 'Current Liabilities',
                'liability_credit_card': 'Current Liabilities',
                'liability_non_current': 'Plus Non-current Liabilities',
                'equity_unaffected': 'Unallocated Earnings',
                'equity': 'Retained Earnings',
            }
            return mapping.get(t, 'Other')

        accounts = Account.search([
            ('company_id', '=', self.company_id.id),
            ('deprecated', '=', False),
        ])

        sections = {
            'assets': {},
            'liabilities': {},
            'equity': {},
        }

        for acc in accounts:
            section = _section_of(acc)
            if not section:
                continue
            subsection = _subsection_of(acc)
            bal = balances.get(acc.id, {})
            debit = bal.get('debit', 0.0)
            credit = bal.get('credit', 0.0)
            balance = bal.get('balance', 0.0)

            comp_bal = comp_balances.get(acc.id, {})
            comp_balance = comp_bal.get('balance', 0.0)

            if balance == 0.0 and comp_balance == 0.0:
                continue

            if subsection not in sections[section]:
                sections[section][subsection] = []

            sections[section][subsection].append({
                'id': acc.id,
                'code': acc.code,
                'name': acc.name,
                'debit': debit,
                'credit': credit,
                'balance': balance,
                'comp_balance': comp_balance,
            })

        return sections

    def get_report_data(self):
        """Main method called by controller – returns full report dict."""
        sections = self._get_account_groups()

        def _sum(rows, key='balance'):
            return sum(r[key] for r in rows)

        def _build_section(section_data, totals_label_map):
            """Build list of subsection dicts with totals."""
            result = []
            grand = 0.0
            grand_comp = 0.0
            for subsection_name, rows in section_data.items():
                sub_total = _sum(rows)
                sub_comp = _sum(rows, 'comp_balance')
                grand += sub_total
                grand_comp += sub_comp
                result.append({
                    'name': subsection_name,
                    'rows': rows,
                    'subtotal': sub_total,
                    'comp_subtotal': sub_comp,
                })
            return result, grand, grand_comp

        assets_subs, total_assets, comp_total_assets = _build_section(
            sections['assets'], {}
        )
        liab_subs, total_liab, comp_total_liab = _build_section(
            sections['liabilities'], {}
        )
        equity_subs, total_equity, comp_total_equity = _build_section(
            sections['equity'], {}
        )

        currency = self.company_id.currency_id

        return {
            'date_to': str(self.date_to or fields.Date.today()),
            'date_from': str(self.date_from) if self.date_from else None,
            'target_move': self.target_move,
            'display_debit_credit': self.display_debit_credit,
            'enable_comparison': self.enable_comparison,
            'comparison_date_to': str(self.comparison_date_to) if self.comparison_date_to else None,
            'company_name': self.company_id.name,
            'currency_symbol': currency.symbol,
            'currency_position': currency.position,
            'assets': assets_subs,
            'total_assets': total_assets,
            'comp_total_assets': comp_total_assets,
            'liabilities': liab_subs,
            'total_liabilities': total_liab,
            'comp_total_liabilities': comp_total_liab,
            'equity': equity_subs,
            'total_equity': total_equity,
            'comp_total_equity': comp_total_equity,
            'total_liabilities_equity': total_liab + total_equity,
            'comp_total_liabilities_equity': comp_total_liab + comp_total_equity,
        }
