# -*- coding: utf-8 -*-
{
    'name': 'POS Product Search Filter',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Add Product search filter to POS Orders screen',
    'description': """
        Adds a 'Product' option to the search autocomplete in the POS Orders (Ticket) screen,
        allowing cashiers to find orders by product name.
    """,
    'author': 'Custom',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_product_search/static/src/js/ticket_screen_patch.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
