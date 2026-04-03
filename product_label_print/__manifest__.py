{
    'name': 'Product Label Print - GP1125T',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Print custom product labels for GP-1125T thermal printer',
    'description': """
        Custom product label printing module for Odoo 19 CE.
        Prints labels with QR code, product code, name, and MRP.
        Optimized for GP-1125T Thermal Transfer Barcode Printer (203 DPI).
        Label style: 2 columns, QR code + KC code + Product Name + MRP Rs.
    """,
    'author': 'Custom',
    'depends': ['product', 'stock', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/product_label_wizard_views.xml',
        'report/product_label_report.xml',
        'report/product_label_template.xml',
        'views/product_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'product_label_print/static/src/css/label_print.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
