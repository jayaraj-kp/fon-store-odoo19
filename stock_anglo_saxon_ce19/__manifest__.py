# -*- coding: utf-8 -*-
{
    'name': 'Stock Anglo-Saxon Accounting for Odoo 19 CE',
    'version': '19.0.5.0.0',
    'category': 'Accounting/Inventory',
    'summary': 'Creates journal entry on purchase receipt validation (Anglo-Saxon style)',
    'description': """
        Odoo 19 CE removed account_anglo_saxon. This module restores:

        1. Journal entry on RECEIPT VALIDATION:
               DR  Stock Valuation Account  (110100)
               CR  Stock Input Account      (230300 GRNI)

        2. Additional lines on VENDOR BILL confirmation:
               DR  Stock Valuation Account  (110100)
               CR  Stock Input Account      (230300 GRNI)

        Reads accounts from stock_account_category_fix custom fields.
    """,
    'author': 'Custom Development',
    'depends': ['stock_account', 'purchase_stock', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
