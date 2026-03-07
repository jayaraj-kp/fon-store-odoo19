# -*- coding: utf-8 -*-
{
    'name': 'Product Multi Barcode & Quantity Packaging',
    'version': '17.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Add multiple barcodes and package quantities to products',
    'description': """
        Add up to 3 barcodes per product with package quantities.
        Scan Barcode 2 -> gets Qty 2 (e.g. 12 for a dozen).
        Scan Barcode 3 -> gets Qty 3 (e.g. 120 for a big carton).
    """,
    'author': 'Custom Module',
    'depends': ['product', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
