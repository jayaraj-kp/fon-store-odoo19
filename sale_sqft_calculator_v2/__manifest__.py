{
    'name': 'Sale Square Feet Calculator',
    'version': '19.0.2.0.0',
    'category': 'Sales',
    'summary': 'Calculate product quantity based on Width x Height (sq.ft)',
    'author': 'TJ Ardor Creations',
    'depends': ['sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/sqft_wizard_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
