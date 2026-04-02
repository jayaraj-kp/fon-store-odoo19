{
    'name': 'POS Cash Transfer',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Transfer cash between POS sessions',
    'description': """
        Transfer cash from one POS session to another.
        - Select source and destination POS
        - Enter transfer amount with reason
        - Automatic journal entries created
        - Full transfer history
    """,
    'author': 'Custom',
    'depends': ['point_of_sale', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_cash_transfer_views.xml',
        'wizard/pos_cash_transfer_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
