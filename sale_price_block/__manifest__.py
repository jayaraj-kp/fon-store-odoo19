{
    'name': 'Block Sale Below Cost Price',
    'version': '19.0.3.0.0',
    'summary': 'Blocks sale & POS order when unit price is below product cost price',
    'description': """
        This module prevents confirming a sale order or processing a POS payment 
        if any order line has a unit price lower than the product's cost price.

        Works on:
        - Sales Orders (blocks on Confirm button)
        - POS Orders (blocks on any payment attempt)
    """,
    'category': 'Sales/Sales',
    'author': 'Your Company',
    'depends': ['sale_management', 'point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'sale_price_block/static/src/js/price_block.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}