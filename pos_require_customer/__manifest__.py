# -*- coding: utf-8 -*-
{
    'name': 'POS Require Customer',
    'version': '19.0.1.0.0',
    'summary': 'Require customer selection before payment in POS',
    'description': """
        Blocks POS payment (Payment button, Cash, Card shortcuts)
        if no customer is selected. Shows a popup notification.
    """,
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
    'auto_install': False,
    'license': 'LGPL-3',
}
