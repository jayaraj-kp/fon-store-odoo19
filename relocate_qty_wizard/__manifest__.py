# -*- coding: utf-8 -*-
{
    'name': 'Relocate Stock Quant with Quantity Adjustment',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Adds a product/quantity table to the Relocate wizard so users can adjust quantities before confirming.',
    'author': 'Custom',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/relocate_qty_wizard_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
