# -*- coding: utf-8 -*-
{
    'name': 'POS Mandatory Customer',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Makes customer selection mandatory before payment in POS',
    'description': """
        This module makes it mandatory to select a customer before
        processing any payment in the Point of Sale.
    """,
    'author': 'Custom',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_mandatory_customer/static/src/js/mandatory_customer.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
