{
    'name': 'POS Payment Button Colors',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Add distinct colors to Cash KDTY and Card KDTY payment buttons in POS',
    'description': """
        This module adds custom colors to the one-click payment buttons in Point of Sale:
        - Cash KDTY: Green color for easy identification
        - Card KDTY: Blue color for easy identification
    """,
    'author': 'Custom',
    'depends': ['point_of_sale'],
    'data': [
        'views/pos_config_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_payment_button_colors/static/src/css/payment_buttons.css',
            'pos_payment_button_colors/static/src/js/payment_button_patch.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
