{
    'name': 'Custom POS Receipt',
    'version': '19.0.1.0.0',
    'summary': 'Rename Discounts, Reduce QR size, Add GST Table',
    'category': 'Point of Sale',
    'author': 'FON Store',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'custom_pos_receipt/static/src/css/custom_receipt.css',
            'custom_pos_receipt/static/src/js/pos_order_gst.js',
            'custom_pos_receipt/static/src/xml/custom_receipt.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}