{
    'name': 'Hide Quick Create on Product Fields',
    'version': '19.0.3.0.0',
    'summary': 'Hides Create and Create and edit options from product fields in Purchase and Sales',
    'author': 'Custom',
    'category': 'Customization',
    'depends': ['purchase', 'sale', 'web'],
    'assets': {
        'web.assets_backend': [
            'hide_quick_create/static/src/js/hide_quick_create.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
