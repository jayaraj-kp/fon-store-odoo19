{
    'name': 'Custom Barcode Label',
    'version': '19.0.4.0.0',
    'summary': 'Custom product barcode label with printer selection wizard and copy count',
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
            'custom_barcode_label/static/src/js/print_label_dialog.js',
            'custom_barcode_label/static/src/xml/print_label_dialog.xml',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
