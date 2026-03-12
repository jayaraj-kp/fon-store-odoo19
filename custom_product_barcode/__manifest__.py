# -*- coding: utf-8 -*-
{
    'name': 'Custom Multi-Barcode & Package Quantity',
    'version': '19.0.21.0.0',
    'summary': 'Scan package barcodes (dozen, bulk pack) with auto quantity & price in POS',
    'category': 'Point of Sale',
    'author': 'Custom Development',
    'website': '',
    'depends': ['product', 'point_of_sale'],
    'data': [
        'views/product_template_views.xml',
    ],
    'assets': {
        # Odoo 19 CE correct bundle name (no leading underscore)
        'point_of_sale.assets_pos': [
            'custom_product_barcode/static/src/js/custom_barcode.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}