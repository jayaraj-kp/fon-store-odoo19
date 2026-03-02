{
    'name': 'Custom POS Receipt QR Size',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Customize POS Receipt QR Code Size',
    'author': 'Your Name',
    'depends': ['point_of_sale'],
    'data': [
        'views/pos_receipt_template.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'custom_pos_receipt/static/src/xml/pos_receipt.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}