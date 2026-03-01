# -*- coding: utf-8 -*-
{
    'name': 'Sale Margin/Cost Block',
    'version': '19.0.1.0.0',
    'summary': 'Block billing/invoicing when cost or margin falls below a configured threshold',
    'description': """
        This module adds margin and cost validation to sales orders and invoices.
        - Configure minimum margin % and/or minimum cost % per company
        - Block order confirmation and invoice creation when thresholds are breached
        - Show clear warning messages with current vs. required values
        - Manager override option via user group
    """,
    'category': 'Sales',
    'author': 'Custom',
    'depends': ['sale', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'security/security_groups.xml',
        'data/res_config_defaults.xml',
        'views/res_config_settings_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
