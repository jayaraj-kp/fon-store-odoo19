# -*- coding: utf-8 -*-
{
    'name': 'POS Product Search Filter',
    'version': '19.0.3.0.0',
    'category': 'Point of Sale',
    'summary': 'Add Product search filter to POS Orders screen',
    'author': 'Custom',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_product_search/static/src/xml/ticket_screen_patch.xml',
            'pos_product_search/static/src/js/ticket_screen_patch.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
