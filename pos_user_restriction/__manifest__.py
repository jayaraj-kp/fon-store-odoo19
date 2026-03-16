# -*- coding: utf-8 -*-
{
    'name': 'POS User Restriction',
    'version': '16.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Restrict users to access only allowed POS configurations',
    'description': """
        This module adds an "Allowed POS" field to res.users.
        When configured, a user can only see and open the POS
        configurations that are explicitly allowed for them.
    """,
    'author': 'Custom',
    'depends': ['point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_users_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
