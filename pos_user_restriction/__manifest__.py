# -*- coding: utf-8 -*-
{
    'name': 'POS User Restriction',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Restrict users to specific Point of Sale terminals',
    'description': """
POS User Restriction
====================
This module allows administrators to assign specific Point of Sale terminals
to individual users. When a user has allowed POS terminals configured:
- The user can only see their assigned POS terminals in the POS dashboard
- The user can only open and operate their assigned terminals
- Admins (without restriction) see all terminals as usual
    """,
    'author': 'Custom',
    'depends': ['point_of_sale', 'base_setup'],
    'data': [
        'security/ir.model.access.csv',
        'security/pos_security.xml',
        'views/res_users_views.xml',
        'views/pos_config_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
