{
    'name': 'Auto Logout',
    'version': '19.0.1.0.0',
    'summary': 'Automatically logout inactive users after a defined timeout',
    'description': """
        Auto Logout Module for Odoo 19 Community Edition
        =================================================
        Automatically logs out inactive users after a configurable timeout period.

        Features:
        - Configure timeout from Technical > Auto Logout Settings menu
        - Warning notification 1 minute before logout
        - Timer resets on any user activity (mouse, keyboard, scroll, click)
        - Set timeout to 0 to disable auto logout
    """,
    'category': 'Technical',
    'author': 'Custom',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/auto_logout_config_views.xml',
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
