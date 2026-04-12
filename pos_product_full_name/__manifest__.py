# -*- coding: utf-8 -*-
{
    'name': 'POS Product Full Name Display',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Display full product names in POS product list without truncation',
    'description': """
        This module removes the text truncation on product names
        in the Point of Sale product grid, so the full product
        name is always visible.
    """,
    'author': 'Custom',
    'depends': ['point_of_sale'],
    'data': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_product_full_name/static/src/css/pos_product_full_name.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
