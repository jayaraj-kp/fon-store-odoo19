# -*- coding: utf-8 -*-
{
    'name': 'POS Receipt Customization - GST Table & QR Code',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Customize POS receipt: smaller QR code + GST tax summary table',
    'depends': ['point_of_sale'],
    'data': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_receipt_custom/static/src/overrides/receipt.xml',
            'pos_receipt_custom/static/src/overrides/receipt.js',
            'pos_receipt_custom/static/src/overrides/receipt.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}