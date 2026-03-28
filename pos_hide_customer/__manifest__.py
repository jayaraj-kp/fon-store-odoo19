{
    'name': 'POS Hide Customer Button',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Hides the Customer button in POS order screen',
    'author': 'Custom',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_hide_customer/static/src/xml/hide_customer_button.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
