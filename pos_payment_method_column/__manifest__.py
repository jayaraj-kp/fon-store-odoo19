{
    'name': 'POS Orders Payment Method Column',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Adds Payment Method column to POS Orders list',
    'description': """
        Adds a Payment Method column to the Point of Sale Orders list screen,
        showing how each order was paid (Cash, Card, etc.).
    """,
    'author': 'Custom',
    'depends': ['point_of_sale'],
    'data': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_payment_method_column/static/src/js/OrderRow.js',
            'pos_payment_method_column/static/src/xml/OrderRow.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
