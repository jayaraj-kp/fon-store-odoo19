# -*- coding: utf-8 -*-
{
    'name': 'Stock Anglo-Saxon Accounting for Odoo 19 CE',
    'version': '19.0.9.0.0',
    'category': 'Accounting/Inventory',
    'summary': 'Anglo-Saxon journal entries on receipt AND delivery validation',
    'description': """
        Odoo 19 CE removed account_anglo_saxon. This module restores:

        PURCHASE RECEIPT validation entry:
            DR  110100 Stock Valuation
            CR  230300 Stock Interim (Received) / GRNI

        DELIVERY (SALES) validation entry:
            DR  121200 Stock Interim (Delivered)
            CR  110100 Stock Valuation

        CUSTOMER INVOICE (standard Odoo 19 + account fix):
            DR  600000 Expenses (COGS)
            CR  121200 Stock Interim (Delivered)  ← clears the interim

        POS SESSION CLOSING:
            Same delivery entry created immediately after POS picking.
            Analytic account resolved from picking's warehouse, not env.user.

        Reads all accounts from stock_account_category_fix custom fields.
        Requires: stock_account_category_fix module.
    """,
    'author': 'Custom Development',
    'depends': [
        'stock_account',
        'purchase_stock',
        'account',
        'point_of_sale',
        'stock_account_category_fix',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
