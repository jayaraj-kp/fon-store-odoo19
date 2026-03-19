# -*- coding: utf-8 -*-
{
    'name': 'POS Charity Ledger',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Allow customers to donate change/custom amount to charity from POS payment screen',
    'description': """
        POS Charity Ledger
        ==================
        This module adds a "Charity" button in the POS payment screen.
        When a customer has change (e.g. paid ₹1000 for ₹999 order),
        they can choose to donate any amount (up to the change) to a
        charity account/ledger instead of receiving it back.

        Features:
        - Charity button on POS payment screen
        - Input any amount up to available change
        - Amount posted to a configurable charity account (no accounting module needed)
        - Charity donation report per session/date
        - Configurable charity account per POS config
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
            'pos_charity_ledger/static/src/js/charity_button.js',
            'pos_charity_ledger/static/src/js/charity_popup.js',
            'pos_charity_ledger/static/src/xml/charity_button.xml',
            'pos_charity_ledger/static/src/xml/charity_popup.xml',
            'pos_charity_ledger/static/src/css/charity.css',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
