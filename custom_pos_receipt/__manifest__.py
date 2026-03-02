{
    'name': 'POS Receipt Custom GST',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'depends': ['point_of_sale'],
    'data': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_receipt_custom/static/src/overrides/receipt.css',
            'pos_receipt_custom/static/src/overrides/receipt.js',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}