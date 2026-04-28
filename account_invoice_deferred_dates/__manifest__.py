# -*- coding: utf-8 -*-
{
    'name': 'Invoice Lines Deferred Dates',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Add Start Date and End Date to Invoice Lines for Deferred Entries',
    'description': """
        This module adds Start Date and End Date fields to account move lines
        (invoice lines) to support deferred revenue/expense accounting entries.
        
        Features:
        - Start Date field on invoice lines
        - End Date field on invoice lines
        - Fields visible as optional columns in Invoice Lines tab
        - Fields carried over to journal items
    """,
    'author': 'Custom Development',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_line_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
