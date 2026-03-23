{
    'name': 'POS Cash Transfer Between Counters',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Transfer cash between POS sessions/counters',
    'author': 'FON-STORE Custom',
    'depends': ['point_of_sale', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/pos_cash_transfer_views.xml',
        'views/pos_config_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
