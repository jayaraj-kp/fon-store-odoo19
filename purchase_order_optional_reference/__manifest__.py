{
    'name': 'Purchase Order Optional Fields',
    'version': '1.0',
    'category': 'Purchases',
    'summary': 'Make Purchase Order and Order Line fields optional during import',
    'description': """
        This module makes optional the following fields in Purchase Order and Purchase Order Lines:
        - Purchase Order: 'Order Reference' (name) field
        - Purchase Order Line: 'Description' (name) field
        
        This allows you to import purchase orders and order lines without providing these values,
        which are normally mandatory. Values can be set later if needed.
    """,
    'author': 'Your Company',
    'depends': ['purchase'],
    'data': [
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
