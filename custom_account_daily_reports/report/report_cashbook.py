import time
from odoo import api, models, _
from odoo.exceptions import UserError


class ReportCashBook(models.AbstractModel):
    _name = 'report.custom_account_daily_reports.report_cashbook'
    _description = 'Cash Book'

    def _get_account_move_entry(self, accounts, init_balance, sortby, display_account):
        cr = self.env.cr
        context = dict(self.env.context or {})

        # Build the list of accounts if none selected
        if not accounts:
            journals = self.env['account.journal'].search([('type', '=', 'cash')])
            accounts = self.env['account.account']
            for journal in journals:
                if journal.default_account_id:
                    accounts += journal.default_account_id
                for acc_out in journal.outbound_payment_method_line_ids:
                    if acc_out.payment_account_id:
                        accounts += acc_out.payment_account_id
                for acc_in in journal.inbound_payment_method_line_ids:
                    if acc_in.payment_account_id:
                        accounts += acc_in.payment_account_id

        # Handle case where still no accounts found
        if not accounts:
            return []

        move_lines = {x: [] for x in accounts.ids}
        running_balance = {x: 0.0 for x in accounts.ids}

        # ---------- INITIAL BALANCE ----------
        if init_balance and context.get('date_from'):
            init_where = "AND l.date < %s"
            init_params_extra = [context['date_from']]

            # Filter by state
            state = context.get('state')
            if state and state.lower() != 'all':
                init_where += " AND m.state = %s"
                init_params_extra.append(state)

            # Filter by journal
            if context.get('journal_ids'):
                init_where += " AND l.journal_id IN %s"
                init_params_extra.append(tuple(context['journal_ids']))

            sql = """
                SELECT 0 AS lid, 
                       l.account_id AS account_id, '' AS ldate, '' AS lcode, 
                       0.0 AS amount_currency,'' AS lref,'Initial Balance' AS lname, 
                       COALESCE(SUM(l.credit),0.0) AS credit,
                       COALESCE(SUM(l.debit),0.0) AS debit,
                       COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit),0) AS balance, 
                       '' AS lpartner_id,'' AS move_name, '' AS currency_code,NULL AS currency_id,'' AS partner_name,
                       '' AS mmove_id, '' AS invoice_id, '' AS invoice_type,'' AS invoice_number
                FROM account_move_line l 
                LEFT JOIN account_move m ON (l.move_id = m.id) 
                LEFT JOIN res_currency c ON (l.currency_id = c.id) 
                LEFT JOIN res_partner p ON (l.partner_id = p.id) 
                JOIN account_journal j ON (l.journal_id = j.id) 
                JOIN account_account acc ON (l.account_id = acc.id)
                WHERE l.account_id IN %s
                  AND l.display_type NOT IN ('line_section', 'line_note')
                  AND m.state != 'cancel'
                  """ + init_where + """
                GROUP BY l.account_id
            """
            params = [tuple(accounts.ids)] + init_params_extra
            cr.execute(sql, params)
            for row in cr.dictfetchall():
                acc_id = row.pop('account_id')
                running_balance[acc_id] = row['balance']
                move_lines[acc_id].append(row)

        # ---------- REGULAR LINES ----------
        sql_sort = 'l.date, l.move_id'
        if sortby == 'sort_journal_partner':
            sql_sort = 'j.code, p.name, l.move_id'

        # Build WHERE clause from context
        extra_where = ""
        extra_params = []

        # Date filters
        if context.get('date_from'):
            extra_where += " AND l.date >= %s"
            extra_params.append(context['date_from'])
        if context.get('date_to'):
            extra_where += " AND l.date <= %s"
            extra_params.append(context['date_to'])

        # State filter
        state = context.get('state')
        if state and state.lower() != 'all':
            extra_where += " AND m.state = %s"
            extra_params.append(state)

        # Journal filter
        if context.get('journal_ids'):
            extra_where += " AND l.journal_id IN %s"
            extra_params.append(tuple(context['journal_ids']))

        sql = """
            SELECT l.id AS lid, l.account_id AS account_id, l.date AS ldate, j.code AS lcode,
                   l.currency_id, l.amount_currency, l.ref AS lref, l.name AS lname,
                   COALESCE(l.debit, 0.0) AS debit, COALESCE(l.credit, 0.0) AS credit,
                   COALESCE(l.debit, 0.0) - COALESCE(l.credit, 0.0) AS balance,
                   m.name AS move_name, c.symbol AS currency_code, p.name AS partner_name
            FROM account_move_line l
            JOIN account_move m ON (l.move_id=m.id)
            LEFT JOIN res_currency c ON (l.currency_id=c.id)
            LEFT JOIN res_partner p ON (l.partner_id=p.id)
            JOIN account_journal j ON (l.journal_id=j.id)
            JOIN account_account acc ON (l.account_id = acc.id)
            WHERE l.account_id IN %s
              AND l.display_type NOT IN ('line_section', 'line_note')
              AND m.state != 'cancel'
              """ + extra_where + """
            GROUP BY l.id, l.account_id, l.date, j.code, l.currency_id, l.amount_currency, l.ref, l.name, m.name, c.symbol, p.name
            ORDER BY """ + sql_sort + """
        """
        params = [tuple(accounts.ids)] + extra_params
        cr.execute(sql, params)

        for row in cr.dictfetchall():
            acc_id = row.pop('account_id')
            current_bal = running_balance.get(acc_id, 0.0) + (row['debit'] - row['credit'])
            running_balance[acc_id] = current_bal
            row['balance'] = current_bal
            move_lines[acc_id].append(row)

        # ---------- AGGREGATION ----------
        account_res = []
        for account in accounts:
            currency = account.currency_id or self.env.company.currency_id
            res = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance'])
            res['code'] = account.code
            res['name'] = account.name
            res['move_lines'] = move_lines[account.id]
            for line in res.get('move_lines'):
                res['debit'] += line['debit']
                res['credit'] += line['credit']
                res['balance'] = line['balance']
            if display_account == 'all':
                account_res.append(res)
            elif display_account == 'movement' and res.get('move_lines'):
                account_res.append(res)
            elif display_account == 'not_zero' and not currency.is_zero(res['balance']):
                account_res.append(res)
        return account_res

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form') or not self.env.context.get('active_model'):
            raise UserError(_("Form content is missing, this report cannot be printed."))
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_ids', []))
        init_balance = data['form'].get('initial_balance', True)
        display_account = data['form'].get('display_account')

        sortby = data['form'].get('sortby', 'sort_date')
        codes = []

        if data['form'].get('journal_ids', False):
            codes = [journal.code for journal in
                     self.env['account.journal'].browse(data['form']['journal_ids'])]
        account_ids = data['form'].get('account_ids', [])
        accounts = self.env['account.account'].browse(account_ids)
        if not accounts:
            journals = self.env['account.journal'].search([('type', '=', 'cash')])
            accounts = self.env['account.account']
            for journal in journals:
                if journal.default_account_id:
                    accounts += journal.default_account_id
                for acc_out in journal.outbound_payment_method_line_ids:
                    if acc_out.payment_account_id:
                        accounts += acc_out.payment_account_id
                for acc_in in journal.inbound_payment_method_line_ids:
                    if acc_in.payment_account_id:
                        accounts += acc_in.payment_account_id
        record = self.with_context(data['form'].get('comparison_context', {}))._get_account_move_entry(accounts, init_balance, sortby, display_account)
        return {
            'doc_ids': docids,
            'doc_model': model,
            'data': data['form'],
            'docs': docs,
            'time': time,
            'Accounts': record,
            'print_journal': codes,
        }
