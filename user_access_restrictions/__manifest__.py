# -*- coding: utf-8 -*-
{
    'name': 'User Access & Restrictions',
    'version': '19.0.1.1.0',
    'category': 'Tools',
    'summary': 'Granular access restrictions per user for cost, reports, and inventory',
    'description': """
User Access & Restrictions
===========================
Adds "Access & Restrictions" tab on the user form.

Restrictions enforced at:
  - Python/ORM level (read, write overrides)
  - JavaScript/DOM level (field & menu hiding)
    """,
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
            'user_access_restrictions/static/src/js/access_restrictions.js',
            'user_access_restrictions/static/src/css/access_restrictions.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
