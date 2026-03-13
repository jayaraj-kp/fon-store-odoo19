# -*- coding: utf-8 -*-
{
    'name': 'Custom Barcode Label Small (27x12mm)',
    'version': '19.0.1.0.0',
    'summary': 'Print small 27x12mm barcode labels for products',
    'description': """
        Adds a separate print wizard for printing small 27×12mm barcode labels.
        Works independently alongside the large 50×25mm label module.
    """,
    'author': 'Custom',
    'category': 'Inventory',
    'depends': ['product', 'stock', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/print_small_label_wizard.xml',
        'report/small_label_report.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'custom_barcode_label_small/static/src/css/print_small_label_dialog.css',
            'custom_barcode_label_small/static/src/js/print_small_label_dialog.js',
            'custom_barcode_label_small/static/src/xml/print_small_label_dialog.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
