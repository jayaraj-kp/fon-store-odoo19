# -*- coding: utf-8 -*-
{
    'name': 'Sales Contacts Menu',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Adds Contacts menu under Sales > Orders showing only Cash Customer contacts',
    'description': """
        This module adds a "Contacts" menu item under Sales > Orders.
        It lists only the contacts (child partners) created under the 
        "Cash Customer" parent partner.
    """,
    'author': 'Custom',
    'depends': ['sale_management', 'contacts'],
    'data': [
        'views/sales_contacts_menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
