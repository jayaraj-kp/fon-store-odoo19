{
    'name': 'Custom Product Label 50x25mm',
    'version': '19.0.1.0.0',
    'summary': 'Custom product barcode label 50x25mm roll - logo, QR, MRP',
    'author': 'Custom',
    'category': 'Inventory',
    'depends': ['stock', 'product'],
    'data': [
        'report/report_product_label.xml',
        'views/product_label_action.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
