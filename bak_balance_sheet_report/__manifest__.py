# -*- coding: utf-8 -*-
{
    'name': 'Balance Sheet Inline Report',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Renders Balance Sheet as an inline browser report with PDF/XLSX export',
    'description': """
        Extends base_accounting_kit to display Balance Sheet as an
        inline HTML report (similar to Odoo Enterprise account_reports),
        with filters, PDF export, and XLSX export support.
    """,
    'author': 'Custom',
    'depends': ['base_accounting_kit', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/balance_sheet_inline_views.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'bak_balance_sheet_report/static/src/css/balance_sheet.css',
            'bak_balance_sheet_report/static/src/js/balance_sheet_action.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
