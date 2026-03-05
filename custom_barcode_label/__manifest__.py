{
    'name': 'Custom Barcode Label',
    'version': '19.0.5.0.0',
    'summary': 'Barcode label printing with print-preview dialog (like invoices)',
    'author': 'Your Company',
    'category': 'Inventory',
    'depends': ['product', 'stock', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/print_label_wizard.xml',
        'report/product_label_report.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'custom_barcode_label/static/src/css/print_label_dialog.css',
            'custom_barcode_label/static/src/js/print_label_dialog.js',
            'custom_barcode_label/static/src/xml/print_label_dialog.xml',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
