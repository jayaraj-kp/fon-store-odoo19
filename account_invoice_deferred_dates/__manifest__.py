# -*- coding: utf-8 -*-
{
    'name': 'Invoice Deferred Entries',
    'version': '19.0.2.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Deferred Expense/Revenue entries from Invoice Lines (without account_accountant)',
    'description': """
        Adds Start Date and End Date to invoice lines and auto-generates
        monthly deferred journal entries — works on Odoo 19 CE Invoicing
        module without requiring the full Accounting (account_accountant) module.

        Features:
        - Start Date and End Date on invoice lines
        - Deferred Account field on invoice lines (balance sheet account)
        - Smart button on confirmed bills showing count of deferred entries
        - Auto-generate equal monthly journal entries on bill confirmation
        - View and delete generated deferred entries from the smart button
        - Validation: End Date must be >= Start Date
    """,
    'author': 'Custom Development',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_line_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
