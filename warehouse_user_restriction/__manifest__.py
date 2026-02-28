{
    'name': 'Warehouse User Restriction',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Restrict users to specific warehouses across Sales, Purchase, Inventory and POS',
    'author': 'Custom',
    'depends': ['stock', 'sale_management', 'purchase', 'point_of_sale'],
    'data': [
        'security/warehouse_restriction_rules.xml',
        'views/res_users_views.xml',
        'views/pos_config_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
