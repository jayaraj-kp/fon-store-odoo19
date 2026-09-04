{
    'name': 'Product Warranty Tracking',
    'version': '19.0.1.0.0',
    'summary': 'Track per-unit warranty using serial numbers, starting from the sale/POS order date.',
    'description': """
Product Warranty Tracking
==========================
- Add a "Warranty (Months)" field on the product form.
- Automatically compute Sale Date, Warranty End Date and Warranty Status
  for every Lot/Serial Number, based on when that specific unit was
  delivered to a customer (works for both Sales Orders and POS Orders).
- A dedicated "Warranty" menu lets staff search by serial number and
  instantly see whether a returned product is still under warranty.
""",
    'category': 'Inventory',
    'author': 'Custom',
    'depends': ['product', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/stock_lot_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
