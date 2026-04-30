# -*- coding: utf-8 -*-
{
    'name': 'Stock Anglo-Saxon Accounting for Odoo 19 CE',
    'version': '19.0.7.0.0',
    'category': 'Accounting/Inventory',
    'summary': 'Anglo-Saxon journal entries on receipt AND delivery validation',
    'description': """
        Odoo 19 CE removed account_anglo_saxon. This module restores:

        1. RECEIPT VALIDATION journal entry:
               DR  110100 Stock Valuation
               CR  230300 Stock Interim (Received) / GRNI

        2. DELIVERY VALIDATION journal entry:
               DR  121200 Stock Interim (Delivered)
               CR  110100 Stock Valuation

        3. CUSTOMER INVOICE (standard Odoo 19 + fixed accounts):
               DR  600000 Expenses (COGS)
               CR  121200 Stock Interim (Delivered)  ← now correct

        Reads all accounts from stock_account_category_fix custom fields.
    """,
    'author': 'Custom Development',
    'depends': ['stock_account', 'purchase_stock', 'account' ,'point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
