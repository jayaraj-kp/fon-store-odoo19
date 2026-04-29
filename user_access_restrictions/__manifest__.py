# -*- coding: utf-8 -*-
{
    'name': 'User Access & Restrictions',
    'version': '19.0.1.0.0',
    'category': 'Tools',
    'summary': 'Granular access restrictions per user for cost, reports, and inventory',
    'description': """
User Access & Restrictions
===========================
This module adds a new tab "Access & Restrictions" on the user form with:

**Product / Cost Restrictions:**
- Hide Cost Price from user
- Prevent Cost Price editing
- Hide Sales Price
- Hide Barcode
- Hide Tax fields
- Hide Internal Reference

**Reports Restrictions:**
- Hide Balance Sheet
- Hide Profit & Loss Account
- Hide Partner Ledger
- Hide General Ledger
- Hide Trial Balance
- Hide Cash Flow Statement
- Hide Aged Receivable
- Hide Aged Payable

**Inventory Restrictions:**
- Hide Scrap Menu
- Hide Physical Inventory Adjustment
- Hide Inventory Valuation
- Hide Replenishment Menu
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
