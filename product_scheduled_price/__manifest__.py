{
    'name': 'Product Scheduled Price',
    'version': '19.0.1.0.0',
    'summary': 'Temporary product price between two dates, without changing the Sales Price field',
    'category': 'Sales',
    'depends': ['product', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
