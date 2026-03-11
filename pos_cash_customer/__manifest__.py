# -*- coding: utf-8 -*-
{
    'name': 'POS Cash Customer',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Single CASH CUSTOMER partner for POS - all walk-in customers saved as contacts under it',
    'description': """
        This module modifies the POS customer creation flow:
        - Only ONE master partner exists: CASH CUSTOMER
        - All new customers created in POS are saved as child contacts under CASH CUSTOMER
        - The POS customer tab is customized to reflect this behavior
    """,
    'author': 'Custom',
    'depends': ['point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'data/cash_customer_data.xml',
        'views/res_partner_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_cash_customer/static/src/js/pos_cash_customer.js',
            'pos_cash_customer/static/src/xml/pos_cash_customer.xml',
            'pos_cash_customer/static/src/css/pos_cash_customer.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
