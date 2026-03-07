{
    'name': 'POS Auto Invoice on Payment',
    'version': '19.0.1.0.0',
    'summary': 'Automatically create invoice when Cash or Card payment is validated in POS',
    'description': """
        Auto-Invoice POS Orders
        =======================
        • Sets to_invoice = True automatically when any payment button is clicked.
        • Works with Cash, Card, and all other POS payment methods.
        • Falls back gracefully when no customer is set (uses POS default partner).
        • Server-side safety: also enforces invoice creation via model override.
        • Compatible with custom_pos_receipt module.
    """,
    'category': 'Point of Sale',
    'author': 'FON Store',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'custom_pos_auto_invoice/static/src/js/auto_invoice.js',
            'custom_pos_auto_invoice/static/src/xml/auto_invoice.xml',
        ],
    },
    'data': [],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
