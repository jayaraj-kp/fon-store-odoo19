{
    'name': 'Sale Order Line Rack Field',
    'version': '19.0.2.0.0',
    'summary': 'Adds a Rack (stock location) field to Sale Order Lines',
    'author': 'Custom',
    'category': 'Sales',
    'depends': ['sale_management', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
