{
    'name': 'POS Customer Validation',
    'version': '1.0',
    'category': 'Point of Sale',
    'summary': 'Validate customer selection before payment in POS',
    'description': '''
        This module prevents users from proceeding with Cash KDTY and Card KDTY payments
        without selecting a customer. A popup message will appear if no customer is selected.
    ''',
    'author': 'Your Company',
    'license': 'LGPL-3',
    'depends': ['point_of_sale'],
    'data': [
        'views/pos_config_views.xml',
    ],
    'installable': True,
    'application': False,
    'assets': {
    'point_of_sale.assets': [
        'pos_customer_validation/static/src/js/payment_validation.js',
    ],
},
}
