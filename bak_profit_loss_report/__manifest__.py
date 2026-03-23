# -*- coding: utf-8 -*-
{
    'name': 'Profit & Loss Inline Report',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Profit & Loss rendered as an inline browser page with PDF/XLSX export',
    'author': 'Custom',
    'depends': ['base_accounting_kit'],
    'data': [
        'security/ir.model.access.csv',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
