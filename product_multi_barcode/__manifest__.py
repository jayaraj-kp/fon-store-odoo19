# -*- coding: utf-8 -*-
{
    'name': 'Product Multi Barcode & Quantity Packaging',
    'version': '1.0.0',
    'category': 'Inventory',
    'summary': 'Add multiple barcodes and package quantities to products',
    'author': 'Custom Module',
    'depends': ['product', 'stock', 'point_of_sale'],
    'data': [
        'views/product_template_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'product_multi_barcode/static/src/js/multi_barcode_pos.js',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
