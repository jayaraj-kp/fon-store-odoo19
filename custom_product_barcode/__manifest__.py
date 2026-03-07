# -*- coding: utf-8 -*-
{
    'name': 'Custom Multi-Barcode & Package Quantity',
    'version': '19.0.14.0.0',
    'summary': 'Scan package barcodes (dozen, bulk pack) with auto quantity & price in POS',
    'description': """
Custom Multi-Barcode & Package Quantity
========================================
Adds two extra barcode fields + package quantity fields to products:

  ┌─────────────┬──────────────┬───────────────────────────────┐
  │  Barcode    │  Qty Field   │  Example                      │
  ├─────────────┼──────────────┼───────────────────────────────┤
  │  Barcode    │  1 unit      │  Standard single-item scan    │
  │  Barcode 2  │  Package Qty1│  1 Dozen → 12 units           │
  │  Barcode 3  │  Package Qty2│  10 Dozen bulk → 120 units    │
  └─────────────┴──────────────┴───────────────────────────────┘

Point of Sale behaviour:
  - Scan standard barcode  → adds 1 unit at unit price
  - Scan Barcode 2         → adds Package Qty 1 at (unit price × qty)
  - Scan Barcode 3         → adds Package Qty 2 at (unit price × qty)
    """,
    'category': 'Point of Sale',
    'author': 'Custom Development',
    'website': '',
    'depends': ['product', 'point_of_sale'],
    'data': [
        'views/product_template_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'custom_product_barcode/static/src/js/custom_barcode.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
