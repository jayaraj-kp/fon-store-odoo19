# -*- coding: utf-8 -*-
{
    'name': 'User Access & Restrictions',
    'version': '19.0.1.2.0',
    'category': 'Tools',
    'summary': 'Granular access restrictions per user — cost, reports, inventory menus',
    'author': 'Custom',
    'depends': [
        'base',
        'product',
        'account',
        'stock',
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_users_views.xml',
        'views/product_views.xml',
        'views/report_menu_views.xml',
        'views/stock_menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'user_access_restrictions/static/src/css/access_restrictions.css',
            'user_access_restrictions/static/src/js/access_restrictions.js',
            'user_access_restrictions/static/src/js/menu_debugger.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
