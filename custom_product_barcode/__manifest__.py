# -*- coding: utf-8 -*-
{
    'name': 'Custom Multi-Barcode & Package Quantity',
    'version': '19.0.22.0.0',
    'summary': 'Scan package barcodes (dozen, bulk pack) with auto quantity, price & per-bill combo limit in POS',
    'description': """
Custom Multi-Barcode & Package Quantity
========================================
Adds two extra barcode fields + package quantity fields + combo limit to products:

  ┌─────────────┬──────────────┬─────────────────┬───────────────────────────────┐
  │  Barcode    │  Qty Field   │  Max Combo Qty  │  Example                      │
  ├─────────────┼──────────────┼─────────────────┼───────────────────────────────┤
  │  Barcode    │  1 unit      │  —              │  Standard single-item scan    │
  │  Barcode 2  │  Package Qty1│  e.g. 5         │  1 Dozen → 12 units, max 5/bill│
  │  Barcode 3  │  Package Qty2│  e.g. 2         │  Bulk pack → 120 units, max 2 │
  └─────────────┴──────────────┴─────────────────┴───────────────────────────────┘

Point of Sale behaviour:
  - Scan standard barcode  → adds 1 unit at unit price (no limit)
  - Scan Barcode 2         → adds Package Qty 1; blocked after Max Combo Qty 1 scans per bill
  - Scan Barcode 3         → adds Package Qty 2; blocked after Max Combo Qty 2 scans per bill
  - Max Combo Qty = 0      → unlimited (no restriction)
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
