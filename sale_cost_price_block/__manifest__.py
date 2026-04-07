# -*- coding: utf-8 -*-
{
    'name': 'Block Sale Below Cost Price',
    'version': '19.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Prevent sales below product cost price in Sales and POS',
    'description': """
        This module blocks sales orders and POS orders when the unit price
        is set below the product's cost price. A warning message is displayed
        and the user is prevented from confirming the order.
        
        Features:
        - Blocks sale order lines with price below cost
        - Blocks POS order lines with price below cost
        - Configurable per company (enable/disable)
        - Option to allow managers to override
        - Clear warning messages with cost price details
    """,
    'author': 'Custom Development',
    'depends': [
        'sale_management',
        'point_of_sale',
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'sale_cost_price_block/static/src/js/cost_price_check.js',
            'sale_cost_price_block/static/src/xml/cost_price_warning.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
