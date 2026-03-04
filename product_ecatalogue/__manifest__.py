# -*- coding: utf-8 -*-
{
    'name': 'Product E-Catalogue',
    'version': '19.0.1.0.0',
    'summary': 'Add E-Catalogue tab with multiple images to product form',
    'description': """
        Adds an E-Catalogue tab on the product form with:
        - Enable/Disable E-Catalogue toggle
        - Cover Image
        - Terms & Conditions
        - Multiple attached images (gallery)
    """,
    'category': 'Inventory/Products',
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': ['product'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_image_views.xml',
        'views/product_template_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
