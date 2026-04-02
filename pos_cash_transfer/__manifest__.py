{
    'name': 'POS Cash Transfer',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Transfer cash between POS sessions',
    'description': """
        This module allows transferring cash from one POS session to another.
        - Select source and destination POS
        - Enter transfer amount with reason
        - Automatic journal entries created
        - Full transfer history and audit trail
    """,
    'author': 'Custom',
    'depends': ['point_of_sale', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_cash_transfer_views.xml',
        'views/pos_config_views.xml',
        'wizard/pos_cash_transfer_wizard_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_cash_transfer/static/src/js/CashTransferButton.js',
            'pos_cash_transfer/static/src/xml/CashTransferButton.xml',
            'pos_cash_transfer/static/src/css/pos_cash_transfer.css',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
