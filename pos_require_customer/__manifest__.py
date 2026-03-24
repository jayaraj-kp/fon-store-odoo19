# -*- coding: utf-8 -*-
{
    'name': 'POS Require Customer',
    'version': '19.0.4.0.0',
    'summary': 'Require customer selection before payment in POS',
    'category': 'Point of Sale',
    'author': 'Custom',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_require_customer/static/src/xml/require_customer.xml',
            'pos_require_customer/static/src/js/require_customer.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
