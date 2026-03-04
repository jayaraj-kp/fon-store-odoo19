{
    'name': 'Custom Product Label 50x25mm',
    'version': '19.0.1.0.0',
    'summary': 'Custom product barcode label with logo, QR, MRP - 50x25mm roll',
    'description': """
        Custom Product Label for 50x25mm thermal roll printer.
        Features:
        - Company logo (vertical, left side)
        - Item name in Arial Narrow (top center)
        - MRP price (top right)
        - Barcode (bottom center, no number)
        - Instagram QR code (bottom left)
    """,
    'author': 'Custom',
    'category': 'Inventory',
    'depends': ['stock', 'product'],
    'data': [
        'report/report_product_label.xml',
        'views/product_label_action.xml',
    ],
    'assets': {
        'web.report_assets_common': [
            'custom_product_label/static/src/scss/label_style.scss',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
