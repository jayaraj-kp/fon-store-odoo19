{
    'name': 'POS Orders Payment Method Column',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Adds Payment Method column to POS Orders list',
    'author': 'Custom',
    'depends': ['point_of_sale'],
    'data': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_payment_method_column/static/src/js/order_row_patch.js',
            'pos_payment_method_column/static/src/xml/order_row_patch.xml',
            'pos_payment_method_column/static/src/css/order_row_patch.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
