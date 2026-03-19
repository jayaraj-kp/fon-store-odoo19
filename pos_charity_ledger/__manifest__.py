# -*- coding: utf-8 -*-
{
    'name': 'POS Charity Ledger',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Allow customers to donate change to charity from POS payment screen',
    'description': """
        Adds a Charity donation button on the POS payment screen.
        When a customer overpays (e.g. ₹1000 for ₹999), the cashier
        can donate any amount up to the change to a charity ledger.
    """,
    'author': 'Custom',
    'depends': ['point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'data/charity_account_data.xml',
        'views/pos_config_views.xml',
        'views/pos_charity_ledger_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_charity_ledger/static/src/js/charity_popup.js',
            'pos_charity_ledger/static/src/js/charity_button.js',
            'pos_charity_ledger/static/src/xml/charity_button.xml',
            'pos_charity_ledger/static/src/xml/charity_popup.xml',
            'pos_charity_ledger/static/src/css/charity.css',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
