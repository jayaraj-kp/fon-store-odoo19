{
    'name': 'Sale Order Line Rack Field',
    'version': '19.0.1.0.0',
    'summary': 'Adds a Rack field to Sale Order Lines (Quotation / Invoice Lines)',
    'author': 'Custom',
    'category': 'Sales',
    'depends': ['sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
