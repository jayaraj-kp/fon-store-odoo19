{
    'name': 'POS UPI QR Code on Receipt',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Dynamic UPI QR code on POS receipts — auto-fills exact bill amount',
    'description': """
        Adds a dynamic UPI payment QR code to every POS receipt.
        Customers scan with Google Pay, PhonePe, Paytm or any UPI app
        and the exact bill amount is pre-filled automatically.

        Setup:
        1. Install Python library: pip install "qrcode[pil]"
        2. Install this module in Odoo
        3. Go to Point of Sale → Configuration → Settings
        4. Enter your UPI ID (VPA) and enable QR on receipt
        5. Save and reload POS
    """,
    'author': 'Custom Development',
    'depends': ['point_of_sale'],
    'data': [
        'views/pos_config_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'custom_pos_upi_qr/static/src/app/upi_qr_receipt.js',
            'custom_pos_upi_qr/static/src/app/upi_qr_receipt.xml',
            'custom_pos_upi_qr/static/src/css/upi_qr.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
