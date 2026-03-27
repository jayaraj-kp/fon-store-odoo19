# # -*- coding: utf-8 -*-
# {
#     'name': 'POS Charity Ledger',
#     'version': '19.0.1.0.0',
#     'category': 'Point of Sale',
#     'summary': 'Allow customers to donate change to charity from POS payment screen',
#     'description': """
#         Adds a Charity donation button on the POS payment screen and order screen.
#         When a customer overpays (e.g. ₹1000 for ₹999), the cashier
#         can donate any amount up to the change to a charity ledger.
#         Also shows a Round Off button to quickly donate the rounding difference.
#     """,
#     'author': 'Custom',
#     'depends': ['point_of_sale'],
#     'data': [
#         'security/ir.model.access.csv',
#         'data/charity_account_data.xml',
#         'views/pos_config_views.xml',
#         'views/pos_charity_ledger_views.xml',
#     ],
#     'assets': {
#         'point_of_sale._assets_pos': [
#             'pos_charity_ledger/static/src/js/charity_popup.js',
#             'pos_charity_ledger/static/src/js/charity_button.js',
#             'pos_charity_ledger/static/src/js/charity_order_button_register.js',
#             'pos_charity_ledger/static/src/xml/charity_button.xml',
#             'pos_charity_ledger/static/src/xml/charity_popup.xml',
#             'pos_charity_ledger/static/src/css/charity.css',
#         ],
#     },
#     'installable': True,
#     'application': False,
#     'license': 'LGPL-3',
# }
# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
{
    'name': 'POS Charity Ledger',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Allow customers to donate change to charity from POS payment screen',
    'description': """
        Adds a Charity donation button on the POS payment screen and order screen.
        When a customer overpays (e.g. ₹1000 for ₹999), the cashier
        can donate any amount up to the change to a charity ledger.
        Also shows a Round Off button to quickly donate the rounding difference.
        The closing register shows charity totals collected during the session.
    """,
    'author': 'Custom',
    'depends': ['point_of_sale', 'pos_hr'],
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
            # Patches pos_hr ClosePosPopup — which IS in the main POS bundle
            'pos_charity_ledger/static/src/js/charity_closing_popup.js',
            'pos_charity_ledger/static/src/xml/charity_button.xml',
            'pos_charity_ledger/static/src/xml/charity_popup.xml',
            # Extends pos_hr.ClosePosPopup template with charity section
            'pos_charity_ledger/static/src/xml/charity_closing_popup.xml',
            'pos_charity_ledger/static/src/css/charity.css',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}