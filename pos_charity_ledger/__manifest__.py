# -*- coding: utf-8 -*-
{
    'name': 'POS Charity Ledger',
    'version': '19.0.2.0.0',
    'category': 'Point of Sale',
    'summary': 'Allow customers to donate change to charity; amount is posted to ledger on register close',
    'description': """
        Adds a Charity donation button on the POS order screen and payment screen.
        Donations are accumulated during the session and posted as a single confirmed
        entry to the Charity Account only when the register is closed.
        The Close Register screen shows the total charity amount collected.
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
            'pos_charity_ledger/static/src/js/charity_order_button_register.js',
            'pos_charity_ledger/static/src/js/close_pos_popup_patch.js',
            'pos_charity_ledger/static/src/xml/charity_button.xml',
            'pos_charity_ledger/static/src/xml/charity_popup.xml',
            'pos_charity_ledger/static/src/xml/close_pos_popup_patch.xml',
            'pos_charity_ledger/static/src/css/charity.css',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
