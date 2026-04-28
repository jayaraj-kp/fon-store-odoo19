{
    'name': 'Hide Quick Create on Product Fields',
    'version': '19.0.1.0.0',
    'summary': 'Hides "Create" and "Create and edit..." options from product many2one fields in Purchase and Sales',
    'author': 'Custom',
    'category': 'Customization',
    'depends': ['purchase', 'sale'],
    'data': [
        'views/purchase_order_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
