# -*- coding: utf-8 -*-
{
    'name': 'Scrap Bulk Entry',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Allows bulk scrapping of multiple products in a single entry',
    'description': """
        Scrap Bulk Entry
        ================
        This module adds a Scrap Bulk Entry feature to Odoo Inventory,
        allowing users to scrap multiple products at once from a single form.
        
        Features:
        - Create bulk scrap orders with multiple product lines
        - Set a common source location for all lines or per-line
        - Track scrap reason and notes
        - Draft → Done workflow
    """,
    'author': 'Custom',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/scrap_bulk_entry_views.xml',
        'views/scrap_bulk_entry_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
