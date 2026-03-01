# -*- coding: utf-8 -*-
{
    'name': 'POS Special Offers Quick Access',
    'version': '19.0.1.0.0',
    'summary': 'Add a Special Offers button in POS top menu for quick coupon/discount program management',
    'description': """
        This module adds a "Special Offers" button in the Point of Sale top menu bar.
        Clicking it opens the Discount & Loyalty program form (Coupon creation interface)
        directly without navigating through the backend menus.
    """,
    'author': 'Custom',
    'category': 'Point of Sale',
    'depends': ['point_of_sale', 'loyalty'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_config_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_special_offers/static/src/xml/special_offers_button.xml',
            'pos_special_offers/static/src/js/screens/special_offers_screen.js',
            'pos_special_offers/static/src/css/special_offers.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
