# -*- coding: utf-8 -*-
{
    'name': 'Product Multi Barcode & Quantity Packaging',
    'version': '17.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Add multiple barcodes and package quantities to products for POS and Sales',
    'description': """
        This module allows you to define up to 3 barcodes per product with different 
        package quantities:
        - Barcode 1 / Qty 1 (default unit)
        - Barcode 2 / Qty 2 (e.g., 1 dozen = 12 units)
        - Barcode 3 / Qty 3 (e.g., 10 dozen = 120 units)
        
        When scanning any barcode in POS or Sales Orders, the corresponding 
        package quantity is automatically applied.
    """,
    'author': 'Custom Module',
    'depends': ['product', 'stock', 'point_of_sale', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/product_product_views.xml',
        'views/assets.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
