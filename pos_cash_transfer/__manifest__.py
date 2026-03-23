{
    'name': 'POS Cash Transfer Between Sessions',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Transfer cash between POS sessions/counters',
    'description': """
        This module allows cashiers/managers to transfer cash 
        from one POS session to another POS session directly 
        from the POS interface.
        
        Features:
        - Transfer cash between any open POS sessions
        - Manager approval option
        - Complete transfer history
        - Automatic journal entries
        - Transfer reason/notes
    """,
    'author': 'FON-STORE Custom',
    'depends': ['point_of_sale', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/pos_cash_transfer_views.xml',
        'views/pos_config_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_cash_transfer/static/src/js/CashTransferButton.js',
            'pos_cash_transfer/static/src/js/CashTransferPopup.js',
            'pos_cash_transfer/static/src/xml/CashTransferPopup.xml',
            'pos_cash_transfer/static/src/css/pos_cash_transfer.css',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
