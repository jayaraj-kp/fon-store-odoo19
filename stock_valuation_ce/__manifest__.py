# -*- coding: utf-8 -*-
{
    'name': 'Stock Valuation CE (Odoo 19)',
    'version': '19.0.1.2.0',
    'summary': 'Full Stock Valuation report for Odoo 19 Community Edition',
    'description': """
        Adds the complete Stock Valuation view to Odoo 19 Community Edition including:
        - Stock Valuation list under Inventory > Reporting > Valuation
        - Valuation at Date wizard
        - Columns: Date, Reference, Product, Quantity, Remaining Qty, Unit Value,
          Total Value, Remaining Value, Journal Entry
        - AVCO / FIFO / Standard Price support

        IMPORTANT: After installing this module you must configure your product
        categories to use AVCO or FIFO with Automated valuation so that
        stock.valuation.layer records are created on every stock move.

        INSTALL ORDER: This module requires stock_account to be installed first.
        If you get a registry error, install 'Inventory Valuation' (stock_account)
        manually from Apps before installing this module.
    """,
    'author': 'Custom',
    'category': 'Inventory/Inventory',
    # Explicit dependency chain: account -> stock -> stock_account -> this module.
    # Listing all three guarantees Odoo installs them in the correct order and
    # that stock.valuation.layer exists in the registry before our code loads.
    'depends': [
        'account',
        'stock',
        'stock_account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_valuation_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
