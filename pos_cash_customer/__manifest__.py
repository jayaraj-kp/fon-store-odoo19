# -*- coding: utf-8 -*-
{
    'name': 'POS Cash Customer Default',
    'version': '19.0.1.0.3',
    'category': 'Point of Sale',
    'summary': 'Creates a default CASH CUSTOMER in POS and provides simplified customer creation popup',
    'author': 'Custom',
    'depends': ['point_of_sale'],
    'data': [
        'data/cash_customer_data.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_cash_customer/static/src/css/pos_cash_customer.css',
            'pos_cash_customer/static/src/xml/CreateContactPopup.xml',
            'pos_cash_customer/static/src/js/pos_cash_customer.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
