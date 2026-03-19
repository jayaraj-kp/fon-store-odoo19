# -*- coding: utf-8 -*-
{
    'name': 'Balance Sheet Inline Report',
    'version': '19.0.1.0.2',
    'category': 'Accounting',
    'summary': 'Balance Sheet rendered as an inline browser page with PDF/XLSX export',
    'author': 'Custom',
    'depends': ['base_accounting_kit'],
    'data': [
        'security/ir.model.access.csv',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
