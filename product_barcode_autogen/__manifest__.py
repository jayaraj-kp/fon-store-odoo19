# -*- coding: utf-8 -*-
{
    'name': 'Product Barcode Auto Generator',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Products',
    'summary': 'Auto-generates unique alphanumeric barcodes on product creation',
    'description': """
Product Barcode Auto Generator
================================
Automatically generates a unique alphanumeric barcode (e.g. BC-A3F7K2M9X1Q5)
when a new product is created, if no barcode is manually provided.

Configuration (via Settings → Technical → System Parameters):
  - product_barcode_autogen.barcode_prefix  (default: BC)
  - product_barcode_autogen.barcode_length  (default: 12, range 4-20)
    """,
    'author': 'Custom',
    'depends': ['product'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        # 'views/product_template_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
