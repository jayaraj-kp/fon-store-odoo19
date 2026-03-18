# -*- coding: utf-8 -*-
{
    'name': 'POS Allow Multiple Cash Payment',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Allow multiple cash-type payment methods in a single POS transaction',
    'description': """
        By default, Odoo POS restricts using more than one cash-type payment method
        in a single transaction. This module removes that restriction, allowing
        split payments between Cash and Card (even if Card is configured as Cash type).
    """,
    'author': 'Custom',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_multi_cash/static/src/js/pos_multi_cash.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
