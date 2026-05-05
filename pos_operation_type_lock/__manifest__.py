{
    'name': 'POS Operation Type Lock',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Password protect POS Operation Type changes',
    'description': """
        This module adds a password protection layer on the 
        Operation Type field in POS configuration settings.
        Any attempt to change the Operation Type will require 
        a security password to proceed.
    """,
    'author': 'Custom',
    'depends': ['point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/pos_lock_config_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pos_operation_type_lock/static/src/js/pos_operation_type_lock.js',
            'pos_operation_type_lock/static/src/xml/pos_lock_dialog.xml',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
