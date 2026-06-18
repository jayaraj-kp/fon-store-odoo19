# -*- coding: utf-8 -*-
{
    'name': 'Stock Internal Transfer Journal Entry',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Auto-create journal entries for internal transfers and auto replenishments without core accounting module',
    'description': """
        This module automatically creates journal entries when:
        - An internal stock transfer (picking type = internal) is validated
        - An auto replenishment is triggered and the related transfer is validated

        Journal Entry Created:
            Stock Transfer A/C  DR
            Stock Transfer A/C  CR

        Features:
        - Configurable journal and account per company
        - Works WITHOUT the core accounting (account) module installed
        - Supports multi-company
        - Full audit trail linked to the stock picking
    """,
    'author': 'Custom Development',
    'website': '',
    'depends': [
        'stock',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/account_data.xml',
        'views/res_config_settings_views.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
}
