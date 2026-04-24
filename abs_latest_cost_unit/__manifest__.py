# -*- coding: utf-8 -*-
{
    'name'    : 'Product Cost Based on Latest Purchase Price',
    'version' : '19.0.1.0.0',
    'author'  : 'Custom',
    'category': 'Inventory/Reporting',
    'summary' : 'Displays unit cost as Total Stock Value / Latest Purchase Price',
    'license' : 'LGPL-3',
    'depends' : ['base', 'stock', 'purchase', 'stock_account'],
    'data'    : [
        'security/ir.model.access.csv',
        'views/product_template_view.xml',
        'views/cron_view.xml',
    ],
    'installable' : True,
    'application' : False,
    'auto_install': False,
}
