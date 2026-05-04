{
    'name': 'Stock Account Category Fix',
    'version': '19.0.1.0.0',
    'summary': 'Restores Account Stock Properties section in Product Category form for Odoo 19 CE',
    'description': """
        In Odoo 19 Community Edition, the Account Stock Properties fields
        (Stock Valuation Account, Stock Journal, Stock Input Account, Stock Output Account)
        are missing from the Product Category form when using Perpetual (Automated) valuation.
        This module restores those fields so Anglo-Saxon costing works correctly.
    """,
    'author': 'Custom',
    'category': 'Inventory',
    'depends': ['stock_account'],
    'data': ['views/product_category_views.xml'],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
}
