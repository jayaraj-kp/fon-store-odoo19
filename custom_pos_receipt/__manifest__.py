# -*- coding: utf-8 -*-
{
    'name': 'Custom POS Receipt',
    'version': '19.0.1.0.0',
    'summary': 'QR size reduction, GST table, amount in words, savings label, salutation',
    'category': 'Point of Sale',
    'author': 'Custom',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'custom_pos_receipt/static/src/utils/amount_in_words.js',
            'custom_pos_receipt/static/src/overrides/order_receipt.js',
            'custom_pos_receipt/static/src/overrides/order_receipt.xml',
            'custom_pos_receipt/static/src/overrides/receipt_style.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}