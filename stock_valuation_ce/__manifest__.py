# -*- coding: utf-8 -*-
{
    'name': 'Stock Valuation CE (Odoo 19)',
    'version': '19.0.1.1.0',
    'summary': 'Full Stock Valuation report for Odoo 19 Community Edition',
    'description': """
        Adds the complete Stock Valuation view to Odoo 19 Community Edition including:
        - Installs stock_account (required for valuation layers) automatically
        - Stock Valuation list under Inventory > Reporting > Valuation
        - Valuation at Date wizard
        - Columns: Date, Reference, Product, Quantity, Remaining Qty, Unit Value,
          Total Value, Remaining Value, Journal Entry
        - AVCO / FIFO / Standard Price support

        IMPORTANT: After installing this module you must configure your product
        categories to use AVCO or FIFO with Automated valuation so that
        stock.valuation.layer records are created on every stock move.
    """,
    'author': 'Custom',
    'category': 'Inventory/Inventory',
    # stock_account ships with Odoo CE – listing it here forces Odoo to install
    # it first (creating stock.valuation.layer) before loading this module.
    'depends': ['stock_account'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_valuation_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
