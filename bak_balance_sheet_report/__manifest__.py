# -*- coding: utf-8 -*-
{
    'name': 'Balance Sheet Inline Report',
    'version': '19.0.1.0.1',
    'category': 'Accounting',
    'summary': 'Renders Balance Sheet as an inline browser report with PDF/XLSX export',
    'description': """
        Extends base_accounting_kit to display Balance Sheet as an
        inline HTML report (similar to Odoo Enterprise account_reports),
        with live filters, PDF export, XLSX export, and comparison period.
    """,
    'author': 'Custom',
    'depends': ['base_accounting_kit'],
    'data': [
        'security/ir.model.access.csv',
        'views/balance_sheet_inline_views.xml',
        'views/menu_views.xml',
    ],
    # No web assets needed — JS/CSS are served as static files
    # loaded directly by the QWeb template via /static/ URLs
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
