{
    'name': 'Custom POS Receipt',
    'version': '19.0.1.0.0',
    'summary': 'Advanced POS Receipt with Custom GST, Totals & UPI QR',
    'category': 'Point of Sale',
    'author': 'FON Store',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'custom_pos_receipt/static/src/css/custom_receipt.css',
            'custom_pos_receipt/static/src/js/pos_order_gst.js',
            # UpiQrCode OWL component must be loaded before the XML template
            'custom_pos_receipt/static/src/js/upi_qr_widget.js',
            'custom_pos_receipt/static/src/xml/custom_receipt.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}