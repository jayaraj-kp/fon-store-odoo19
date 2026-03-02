{
    'name': 'Custom POS Receipt',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'custom_pos_receipt2/static/src/xml/custom_receipt.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
}