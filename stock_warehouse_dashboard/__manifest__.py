# # -*- coding: utf-8 -*-
# {
#     'name': 'Stock Warehouse Dashboard – To Send / To Accept',
#     'version': '19.0.2.0.0',
#     'category': 'Inventory',
#     'summary': 'Adds To Send and To Accept counters + Send/Accept buttons to cross-WH transfers',
#     'description': """
# Extends the Inventory Overview to show per-warehouse:
#   - To Send   : Ready/Confirmed outgoing cross-WH internal transfers not yet sent
#   - To Accept : Ready/Confirmed incoming cross-WH internal transfers awaiting acceptance
#
# Workflow:
#   1. Sender opens the transfer and clicks [Send]
#      → Transfer is marked as 'Sent'; To Send counter decreases,
#        To Accept counter at the destination warehouse increases.
#   2. Receiver (or sender) opens the transfer and clicks [Accept]
#      → Transfer is validated immediately; To Accept counter decreases.
#
# Both the sender and receiver can click [Accept] to complete the transfer.
# Clicking either badge on the kanban card opens the filtered transfer list.
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
    'version': '19.0.5.0.0',
    'category': 'Inventory',
    'summary': 'Adds To Send and To Accept counters + Send/Accept buttons to cross-WH transfers',
    'description': """
Extends the Inventory Overview to show per-warehouse:
  - To Send   : Ready/Confirmed outgoing cross-WH internal transfers not yet sent
  - To Accept : Ready/Confirmed incoming cross-WH internal transfers awaiting acceptance

Workflow:
  1. Sender opens the transfer and clicks [Send]
     → Transfer is marked as 'Sent'; To Send counter decreases,
       To Accept counter at the destination warehouse increases.
  2. Receiver (or sender) opens the transfer and clicks [Accept]
     → Transfer is validated immediately; To Accept counter decreases.

Both the sender and receiver can click [Accept] to complete the transfer.
Clicking either badge on the kanban card opens the filtered transfer list.

v3 changes:
  - Auto-replenishment support: write() override catches pickings whose
    locations are filled in after initial creation (procurement rules pattern).
  - Transit location support: warehouse resolved by walking up the location
    parent tree (_resolve_warehouse helper) instead of only checking
    location.warehouse_id directly.
  - 'waiting' state now included in To Send / To Accept counts and actions
    so replenishment-triggered transfers appear immediately.

v4 / v5 changes:
  - Auto-creates journal entries on Send and Accept:
      Send  → Dr Stock Transfer Out  / Cr Stock Valuation
      Accept → Dr Stock Valuation (with WH analytic) / Cr Stock Transfer In
  - Adds accounting configuration tab to the Warehouse form.
  - Smart buttons on the picking form link directly to the created entries.
    """,
    'author': 'FON-STORE',
    'website': '',
    'depends': ['stock', 'account'],
    'data': [
        'views/stock_warehouse_dashboard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'stock_warehouse_dashboard/static/src/scss/warehouse_dashboard.scss',
            'stock_warehouse_dashboard/static/src/js/warehouse_dashboard.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
