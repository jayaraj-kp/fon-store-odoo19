{
    'name': 'Stock Rule Propagation',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Configuration',
    'summary': 'Restores Propagation options in Stock Routing Rules for Odoo 19 CE',
    'description': """
        This module restores the Propagation tab/fields in Stock Rules
        that were removed in Odoo 19 Community Edition.

        Features:
        - Propagation of Procurement Group (Leave Empty / Propagate / Fixed)
        - Propagate Carrier
        - Warehouse to Propagate
        - Full backend logic to propagate values in stock moves
    """,
    'author': 'Custom',
    'depends': ['stock'],
    'data': [
        'views/stock_rule_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
