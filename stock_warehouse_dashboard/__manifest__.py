# -*- coding: utf-8 -*-
{
    'name': 'Stock Warehouse Dashboard – To Send / To Accept',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Adds To Send and To Accept counters to the Inventory Overview kanban',
    'description': """
Extends the Inventory Overview to show per-warehouse:
  ● To Send   – Ready/Confirmed outgoing internal transfers not yet validated
  ● To Accept – Ready/Confirmed incoming internal transfers not yet validated

Clicking either badge opens the filtered transfer list.
    """,
    'author': 'FON-STORE',
    'website': '',
    'depends': ['stock'],
    'data': [
        'views/stock_warehouse_dashboard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'stock_warehouse_dashboard/static/src/scss/warehouse_dashboard.scss',
            'stock_warehouse_dashboard/static/src/js/warehouse_dashboard.js',
            'stock_warehouse_dashboard/static/src/xml/warehouse_dashboard.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
