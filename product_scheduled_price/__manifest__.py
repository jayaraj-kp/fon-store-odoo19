{
    'name': 'Product Scheduled Price',
    'version': '19.0.1.1.0',
    'summary': 'Temporary product price between two dates for Sales and POS, without changing the Sales Price field',
    'category': 'Sales',
    'depends': ['product', 'sale', 'point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'product_scheduled_price/static/src/app/pos_price_refresh.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
