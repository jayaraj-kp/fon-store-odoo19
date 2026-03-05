{
    'name': 'POS Invoice Menu',
    'version': '19.0.1.0.0',
    'summary': 'Add Invoices button in POS top bar and backend menu',
    'category': 'Point of Sale',
    'author': 'Custom',
    'depends': ['point_of_sale'],
    'data': [
        'views/pos_invoice_menu_views.xml',
    ],
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
