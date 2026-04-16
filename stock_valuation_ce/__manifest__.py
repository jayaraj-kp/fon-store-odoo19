# -*- coding: utf-8 -*-
{
    'name': 'Stock Valuation CE (Odoo 19)',
    'version': '19.0.1.0.0',
    'summary': 'Full Stock Valuation report for Odoo 19 Community Edition',
    'description': """
        Adds the complete Stock Valuation view to Odoo 19 Community Edition including:
        - Stock Valuation list under Inventory > Reporting > Valuation
        - Valuation at Date filter
        - Columns: Date, Reference, Product, Quantity, Remaining Qty, Unit Value, Total Value, Remaining Value
        - Journal Entry link (if account_move is available)
        - AVCO / FIFO / Standard Price support
    """,
    'author': 'Custom',
    'category': 'Inventory/Inventory',
    'depends': ['stock', 'stock_account'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_valuation_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
