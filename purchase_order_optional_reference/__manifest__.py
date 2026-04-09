{
    'name': 'Purchase Order Optional Reference',
    'version': '1.0',
    'category': 'Purchases',
    'summary': 'Make Order Reference field optional in Purchase Order',
    'description': """
        This module makes the 'Order Reference' (name) field optional in Purchase Order.
        By default, Odoo makes this field required, but this module changes it to optional.
        This allows you to import purchase orders without providing an Order Reference value.
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
