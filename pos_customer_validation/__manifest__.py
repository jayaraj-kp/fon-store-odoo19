{
    'name': 'POS Customer Validation',
    'version': '1.0',
    'category': 'Point of Sale',
    'summary': 'Validate customer selection before payment in POS',
    'author': 'Your Company',
    'license': 'LGPL-3',
    'depends': ['point_of_sale'],
    'data': [
        'views/pos_config_views.xml',
    ],
    'installable': True,
    'application': False,
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_customer_validation/static/src/js/payment_validation.js',
            'pos_customer_validation/static/src/css/style.css',
        ],
    },
}