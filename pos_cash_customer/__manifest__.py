# -*- coding: utf-8 -*-
{
    'name': 'POS Cash Customer Default',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Creates a default CASH CUSTOMER in POS and customizes the customer creation flow',
    'description': """
        This module:
        1. Auto-creates a default "CASH CUSTOMER" contact on installation
        2. Sets CASH CUSTOMER as the default customer in POS orders
        3. When clicking "Create" in POS customer search, opens a simplified 
           "Create Contact" wizard (like the sub-contact form) instead of full partner form
    """,
    'author': 'Custom',
    'depends': ['point_of_sale'],
    'data': [
        'data/cash_customer_data.xml',
        'views/pos_config_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_cash_customer/static/src/js/CustomerListScreen.js',
            'pos_cash_customer/static/src/js/CreateContactPopup.js',
            'pos_cash_customer/static/src/xml/CustomerListScreen.xml',
            'pos_cash_customer/static/src/xml/CreateContactPopup.xml',
            'pos_cash_customer/static/src/css/pos_cash_customer.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
