{
    'name': 'Hide Quick Create on Product Fields',
    'version': '19.0.2.0.0',
    'summary': 'Hides "Create" and "Create and edit..." options from product many2one fields in Purchase and Sales',
    'author': 'Custom',
    'category': 'Customization',
    'depends': ['purchase', 'sale', 'web'],
    'data': [
        'views/assets.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hide_quick_create/static/src/js/hide_quick_create.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
