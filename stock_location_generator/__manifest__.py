# -*- coding: utf-8 -*-
{
    'name': 'Stock Location Generator',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Generate Rack and Box locations in bulk for a warehouse',
    'description': """
Stock Location Generator
========================
Allows warehouse managers to bulk-generate Rack or Box sub-locations
inside any stock location using a simple wizard (From / To range + optional Prefix).

Features:
- Generate Rack locations (e.g. Rack 1 … Rack 10)
- Generate Box locations inside an existing Rack
- Configurable number prefix/suffix
- Available directly from the Locations list view
    """,
    'author': 'Custom',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/stock_location_generate_wizard_views.xml',
        'views/stock_location_views.xml',
        'views/stock_location_generate_menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
