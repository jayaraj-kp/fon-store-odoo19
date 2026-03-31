{
    'name': 'Sale Square Feet Calculator',
    'version': '19.0.6.0.0',
    'category': 'Sales',
    'summary': 'Calculate product quantity based on Width x Height (sq.ft)',
    'author': 'TJ Ardor Creations',
    'depends': ['sale_management', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/sqft_wizard_views.xml',
        'views/sale_order_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # XML template MUST be listed before the JS that references it
            'sale_sqft_calculator/static/src/xml/sqft_button_field.xml',
            'sale_sqft_calculator/static/src/js/sqft_button_field.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
