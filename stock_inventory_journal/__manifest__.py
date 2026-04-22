# -*- coding: utf-8 -*-
{
    'name': 'Stock Inventory Journal Entry (Odoo 19 CE)',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Auto-create journal entries on physical inventory adjustments in Odoo 19 CE',
    'description': """
        In Odoo 19, physical inventory adjustments no longer create journal entries automatically
        under the Perpetual (at invoicing) valuation method. This module restores that behavior
        by creating a journal entry immediately when a physical inventory adjustment is applied.

        Features:
        - Auto-creates journal entry on Apply of physical inventory adjustment
        - Debits / Credits Stock Valuation account based on quantity increase / decrease
        - Uses the Stock Journal configured on the product category
        - Works with AVCO and FIFO costing methods
        - Links the journal entry back to the stock move for full traceability
    """,
    'author': 'Custom Development',
    'depends': ['stock_account'],
    'data': [
        'views/stock_move_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
