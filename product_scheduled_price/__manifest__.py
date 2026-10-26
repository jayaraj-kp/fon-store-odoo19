{
    'name': 'Product Scheduled Price',
    'version': '19.0.1.0.0',
    'summary': 'Temporary product price between two dates for Sales and POS, without changing the Sales Price field',
    'category': 'Sales',
    'depends': ['product', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'data/ir_cron.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
