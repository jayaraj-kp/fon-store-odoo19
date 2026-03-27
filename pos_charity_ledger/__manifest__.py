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
        At session close, a sticky warning notification reminds the cashier
        of the total charity amount to remove from the cash drawer.
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
            # Closing reminder — patches PosStore.closePos() only.
            # NOTE: Do NOT import ClosePosPopup here — it lives in
            # _assets_pos_closing (a separate lazy bundle) and will
            # cause "module not defined" errors if imported from here.
            'pos_charity_ledger/static/src/js/charity_closing_popup.js',
            'pos_charity_ledger/static/src/xml/charity_button.xml',
            'pos_charity_ledger/static/src/xml/charity_popup.xml',
            # charity_closing_popup.xml is intentionally NOT listed here.
            # The closing reminder is delivered via a notification, not
            # a template extension, to avoid cross-bundle import issues.
            'pos_charity_ledger/static/src/css/charity.css',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}