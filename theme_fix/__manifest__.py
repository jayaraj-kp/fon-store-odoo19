{
    'name': 'Theme Fix',
    'version': '1.0',
    'category': 'Technical',
    'depends': ['web', 'sale'],
    'assets': {
        'web.assets_backend': [
            'theme_fix/static/src/css/fix.css',
        ],
    },
    'views': [
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
