# -*- coding: utf-8 -*-
{
    'name': 'Customer Gender (Male/Female)',
    'version': '19.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'Add Gender (Male/Female) field on Customers and allow filtering by Gender',
    'description': """
Customer Gender
===============
This module adds a "Gender" field (Male / Female) on the Contact / Customer
form (res.partner) and adds ready-to-use Filters and Group By options in the
Contacts / Customers search view so you can quickly filter or group
customers by gender.

Features
--------
- New "Gender" selection field (Male / Female) on res.partner
- Field visible on Contact form view
- Field visible as an optional column in Contact list/tree view
- Search filters: "Male" and "Female"
- Group By: "Gender"
""",
    'author': 'Custom Development',
    'license': 'LGPL-3',
    'depends': ['base', 'contacts'],
    'data': [
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
