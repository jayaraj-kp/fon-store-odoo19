# -*- coding: utf-8 -*-
{
    'name': 'Stock Anglo-Saxon Accounting for Odoo 19 CE',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Inventory',
    'summary': 'Restores Anglo-Saxon inventory accounting journal entries on vendor bill confirmation',
    'description': """
        Odoo 19 CE removed the account_anglo_saxon module and the "Automatic Accounting"
        setting. This module restores the full 4-line journal entry behavior when a
        vendor bill is confirmed for purchased goods.

        Compatible with: stock_account_category_fix (your custom module that adds
        Account Stock Properties fields to Product Category).

        On vendor bill confirmation, creates:
            DR  Stock Valuation Account    (e.g. 110100 - Stock Valuation)
            CR  Stock Input Account        (e.g. 230300 - Stock Interim Received)

        Combined with the standard Odoo lines:
            DR  Stock Input Account        (e.g. 230300 - Stock Interim Received)
            CR  Account Payable            (e.g. 211000 - Account Payable)

        Result: Full 4-line Anglo-Saxon journal entry on bill confirmation.
    """,
    'author': 'Custom Development',
    'depends': [
        'stock_account',
        'purchase_stock',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
