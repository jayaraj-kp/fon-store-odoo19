{
    'name': 'POS Invoice Menu',
    'version': '19.0.1.0.0',
    'summary': 'Add Invoices menu button in POS top bar',
    'description': """
        Adds a custom "Invoices" button to the POS top bar that displays
        all orders/invoices for the current session. Works without the
        core accounting module.
    """,
    'category': 'Point of Sale',
    'author': 'Custom',
    'website': '',
    'depends': ['point_of_sale'],
    'data': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_invoice_menu/static/src/js/InvoiceListScreen.js',
            'pos_invoice_menu/static/src/js/InvoiceButton.js',
            'pos_invoice_menu/static/src/xml/InvoiceListScreen.xml',
            'pos_invoice_menu/static/src/xml/InvoiceButton.xml',
            'pos_invoice_menu/static/src/css/pos_invoice.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
