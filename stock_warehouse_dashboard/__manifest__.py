# # -*- coding: utf-8 -*-
# {
#     'name': 'Stock Warehouse Dashboard – To Send / To Accept',
#     'version': '19.0.1.0.0',
#     'category': 'Inventory',
#     'summary': 'Adds To Send and To Accept counters to the Inventory Overview kanban',
#     'description': """
# Extends the Inventory Overview to show per-warehouse:
#   - To Send   : Ready/Confirmed outgoing internal transfers not yet validated
#   - To Accept : Ready/Confirmed incoming internal transfers not yet validated
#
# Clicking either badge opens the filtered transfer list.
#     """,
#     'author': 'FON-STORE',
#     'website': '',
#     'depends': ['stock'],
#     'data': [
#         'views/stock_warehouse_dashboard_views.xml',
#     ],
#     'assets': {
#         'web.assets_backend': [
#             'stock_warehouse_dashboard/static/src/scss/warehouse_dashboard.scss',
#             'stock_warehouse_dashboard/static/src/js/warehouse_dashboard.js',
#         ],
#     },
#     'installable': True,
#     'application': False,
#     'auto_install': False,
#     'license': 'LGPL-3',
# }
# -*- coding: utf-8 -*-
{
    'name': 'Stock Warehouse Dashboard – To Send / To Accept',
    'version': '19.0.2.0.0',
    'category': 'Inventory',
    'summary': 'Adds To Send and To Accept counters to the Inventory Overview kanban',
    'description': """
Extends the Inventory Overview to show per-warehouse:
  - To Send   : Ready/Confirmed outgoing internal transfers (stock → transit)
  - To Accept : Ready/Confirmed incoming internal transfers (transit → stock)

Clicking either badge opens the filtered transfer list.
The Send/Accept buttons appear on the transfer form view.

Two-step flow (no warehouse config change needed):
  1. Send   → validates leg-1 (stock → transit), auto-creates leg-2
  2. Accept → validates leg-2 (transit → stock)

Existing cross-WH transfers are migrated automatically on install/upgrade.
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
        ],
    },
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}