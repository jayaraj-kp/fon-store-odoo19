{
    'name': 'POS Invoice List Button',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Adds an Invoices button in POS top bar to list all POS invoices',
    'author': 'Custom',
    'depends': ['point_of_sale'],
    'data': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_invoice_list/static/src/js/invoice_screen.js',
            'pos_invoice_list/static/src/js/navbar_patch.js',
            'pos_invoice_list/static/src/xml/invoice_screen.xml',
            'pos_invoice_list/static/src/xml/navbar_patch.xml',
            'pos_invoice_list/static/src/css/invoice_screen.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
