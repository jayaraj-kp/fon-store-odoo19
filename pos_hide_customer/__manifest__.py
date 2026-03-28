{
    'name': 'POS Hide Customer Button',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Hides the Customer button in POS order screen',
    'author': 'Custom',
    'depends': ['point_of_sale'],
    'assets': {
        # Primary bundle for Odoo 19 POS
        'point_of_sale._assets_pos': [
            'pos_hide_customer/static/src/css/hide_customer_button.css',
        ],
        # Fallback for older bundle name
        'web.assets_backend': [
            'pos_hide_customer/static/src/css/hide_customer_button.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
