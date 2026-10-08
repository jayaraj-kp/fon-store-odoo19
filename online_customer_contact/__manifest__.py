{
    'name': 'Online Customer Contacts',
    'version': '19.0.1.1.0',
    'category': 'Sales',
    'summary': 'Keep all online customers as contacts of one "Online Customers" parent',
    'depends': ['sale', 'account'],
    'data': [
        'data/partner_data.xml',
        'views/sale_order_views.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
