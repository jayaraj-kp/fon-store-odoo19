# -*- coding: utf-8 -*-
{
    'name': 'Product Barcode Auto Generator',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Products',
    'summary': 'Auto-generates unique alphanumeric barcodes on product creation',
    'description': """
Product Barcode Auto Generator
================================
Automatically generates a unique alphanumeric barcode when a new product
is created, if no barcode is manually provided.

Features:
- Auto-generates alphanumeric barcode (e.g. BC-A3F7K2M9X1Q5)
- Configurable prefix via Settings
- Works on product.template and product.product (variants)
- Manual barcode entry is still supported (auto-gen is skipped if filled)
- Regenerate button on the product form
    """,
    'author': 'Custom',
    'depends': ['product'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/res_config_settings_views.xml',
        'views/product_template_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
