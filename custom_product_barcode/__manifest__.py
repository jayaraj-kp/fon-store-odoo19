# -*- coding: utf-8 -*-
{
    'name': 'Custom Multi-Barcode & Package Quantity',
    'version': '19.0.26.0.0',
    'summary': 'Scan package barcodes with auto quantity, price & max combo limit per bill',
    'description': """
Custom Multi-Barcode & Package Quantity
========================================
Adds two extra barcode fields + package quantity + price + max combo limit:

  ┌─────────────┬──────────────┬─────────────┬──────────────────┐
  │  Barcode    │  Qty Field   │  Price      │  Max Combo/Bill  │
  ├─────────────┼──────────────┼─────────────┼──────────────────┤
  │  Barcode    │  1 unit      │  unit price │  (standard)      │
  │  Barcode 2  │  Package Qty1│  Price 1    │  Max Combo Lmt 1 │
  │  Barcode 3  │  Package Qty2│  Price 2    │  Max Combo Lmt 2 │
  └─────────────┴──────────────┴─────────────┴──────────────────┘

Max Combo Limit:
  - Default = 5 (can be changed per product)
  - If the package is already added 5 times in the current bill,
    scanning it again will show a warning and BLOCK the addition.
  - Set to 0 for unlimited.
    """,
    'category': 'Point of Sale',
    'author': 'Custom Development',
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
