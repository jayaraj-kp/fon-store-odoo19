# -*- coding: utf-8 -*-
{
    'name': 'Scrap Bulk Entry',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Allows bulk scrapping of multiple products in a single entry',
    'author': 'Custom',
    'depends': ['stock'],
    'data': [
        'data/scrap_bulk_entry_sequence.xml',
        'security/ir.model.access.csv',
        'views/scrap_bulk_entry_views.xml',
        'views/scrap_bulk_entry_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
