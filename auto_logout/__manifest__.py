{
    'name': 'Auto Logout',
    'version': '19.0.1.0.0',
    'summary': 'Automatically logout inactive users after a defined timeout',
    'category': 'Technical',
    'author': 'Custom',
    'depends': ['base', 'web', 'base_setup'],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'auto_logout/static/src/js/auto_logout.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
