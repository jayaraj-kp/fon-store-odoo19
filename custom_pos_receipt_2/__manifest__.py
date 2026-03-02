{
    'name': 'Custom POS Receipt - QR Code Size',
    'version': '1.0',
    'category': 'Point of Sale',
    'summary': 'Reduce QR code size on POS receipt',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'custom_pos_receipt/static/src/xml/pos_receipt.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
}
