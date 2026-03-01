{
    'name': 'Auto Logout',
    'version': '19.0.1.0.0',
    'summary': 'Automatically logout inactive users after a defined timeout',
    'description': """
        Auto Logout Module for Odoo 19 Community Edition
        =================================================
        Automatically logs out inactive users after a configurable timeout period.
        
        Features:
        - Configurable timeout (in minutes) from General Settings
        - Warning notification 1 minute before logout
        - Timer resets on any user activity (mouse, keyboard, scroll, click)
        - Set timeout to 0 to disable auto logout
    """,
    'category': 'Technical',
    'author': 'Custom',
    'website': '',
    'depends': ['base', 'web'],
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
